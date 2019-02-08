import argparse
import os
import time
import json
import numpy as np

from matplotlib import pyplot as plt

from powerusageparser import open_srumutil_data
from batteryusageparser import open_battery_reports
from utils import (
    get_ordered_datalist_battery,
    get_ordered_datalist_power,
    milliwatthours_to_millijoules,
    millijoules_to_milliwatts
)

DIST_BETWEEN_SAMPLES = 60


def analysisparser():
    parser = argparse.ArgumentParser(
        description='Analyze data from a `usagerunfrom<TIME>` folder containing the directories'
                    '`baseline`, and `test`. Analysis performed depends on the flag. Currently '
                    'the only existing analysis is a simple comparison against the baseline.'
    )

    parser.add_argument('--data', type=str, default=None,
                        help='Location of the data (must point to usagerunfrom*).')

    parser.add_argument('--baseline-data', type=str, default=None,
                        help='Sets the baseline data directory. Ignored if --data is specified.')

    parser.add_argument('--baseline-time', type=int, default=None,
                        help='Length of baseline in seconds, default is obtained from the config.')

    parser.add_argument('--test-time', type=int, default=None,
                        help='Length of baseline in seconds, default is obtained from the config.')

    parser.add_argument('--test-data', type=str, default=None,
                        help='Sets the test data directory. Ignored if --data is specified.')

    parser.add_argument('--config-data', type=str, default=None,
                        help='Sets the config to use (a .json). Ignored if --data is specified. '
                             'It can be found in usagerunfrom* folders.')

    parser.add_argument('--compare', '-c', action='store_true', default=False,
                        help='If set, a standard comparison will be performed and results will be '
                              'returned as a JSON and some accompanying matplotlib figures.')

    parser.add_argument('--application', nargs='+', required=True,
                        help='A string that represents the application we should be looking for '
                             'in the given `test` directories `srumuti*.csv` files. i.e. `firefox` '
                             'or `firefox.exe`.')

    parser.add_argument('--baseline-application', nargs='+', default=None,
                        help='Same as application, but for the baseline, by default we use power '
                             'usage measurements from all listed applications. As an example, this '
                             'can be used to compare Firefox idling against Firefox displaying '
                             'a full screen video.')
    parser.add_argument('--exclude-baseline-apps', nargs='+', default=None,
                        help='Same as application, but for the baseline, by default we use power '
                             'usage measurements from all listed applications. As an example, this '
                             'can be used to compare Firefox idling against Firefox displaying '
                             'a full screen video.')
    parser.add_argument('--exclude-test-apps', nargs='+', default=None,
                        help='Same as application, but for the baseline, by default we use power '
                             'usage measurements from all listed applications. As an example, this '
                             'can be used to compare Firefox idling against Firefox displaying '
                             'a full screen video.')

    parser.add_argument('--output', type=str, default=os.getcwd(),
                        help='Location to store output.')

    parser.add_argument('--outputtype', type=str, default='json',
                        help='Type of output to store, can be either `csv` or `json`.')

    parser.add_argument('--smooth-battery', action='store_true', default=False,
                        help='Type of output to store, can be either `csv` or `json`.')

    parser.add_argument('--plot-power', action='store_true', default=False,
                        help='Type of output to store, can be either `csv` or `json`.')

    return parser


def display_results(results, otype):
    if otype == 'json':
        print(results)
    else:
        print()
        for key in results:
            print(key)
            print(results[key])
            print()
    return


def get_avg_consumption_rate(ordered_datalist, total_time):
    consumption = []
    for row in ordered_datalist:
        consumption.append([
            x for x in row
        ])

    avg_consumption = [sum(x)/total_time for x in zip(*consumption)]
    return avg_consumption


def get_battery_deltas(ordered_datalist, timewindow=60):
    deltas = []
    for i in range(len(ordered_datalist)):
        if i >= len(ordered_datalist) - 1:
            continue
        deltas.append(millijoules_to_milliwatts(
            milliwatthours_to_millijoules((ordered_datalist[i]-ordered_datalist[i+1])),
            timewindow
        ))
    return deltas


def compare_data(baselinedir, testdir, config, args):
    app = args['application']
    otype = args['outputtype']

    print("Getting SRUMUTIL baseline data...")
    header, baselinedata = open_srumutil_data(
        baselinedir,
        args['baseline_application'],
        args['exclude_baseline_apps'],
        config['baselinestarttime'] if 'baselinestarttime' in config else 600,
        args['baseline_time']
    )
    print("Getting SRUMUTIL testing data...")
    _, testdata = open_srumutil_data(
        testdir,
        args['application'],
        args['exclude_test_apps'],
        config['teststarttime'],
        args['test_time']
    )

    print("Getting battery reports for baseline...")
    baseline_reports = open_battery_reports(baselinedir)
    print("Getting battery reports for test...")
    test_reports = open_battery_reports(testdir)

    print("Running comparison")

    # Conduct battery usage analysis
    ord_baseline_battery = get_ordered_datalist_battery(baseline_reports)
    ord_test_battery = get_ordered_datalist_battery(test_reports)

    ord_baseline = [float(r[1]) for r in ord_baseline_battery]
    ord_test = [float(r[1]) for r in ord_test_battery]
    print(ord_baseline)

    if args['smooth_battery']:
        N = 15
        cumsum, moving_aves = [0], []

        for i, x in enumerate(ord_baseline, 1):
            cumsum.append(cumsum[i-1] + x)
            if i>=N:
                moving_ave = (cumsum[i] - cumsum[i-N])/N
                #can do stuff with moving_ave here
                moving_aves.append(moving_ave)
        ord_baseline = moving_aves

    deltas_base = get_battery_deltas(ord_baseline, timewindow=60)
    conv_baseline = [(x*60)/3600 for x in deltas_base]

    if args['smooth_battery']:
        N = 15
        cumsum, moving_aves = [0], []

        for i, x in enumerate(deltas_base, 1):
            cumsum.append(cumsum[i-1] + x)
            if i>=N:
                moving_ave = (cumsum[i] - cumsum[i-N])/N
                #can do stuff with moving_ave here
                moving_aves.append(moving_ave)
        deltas_base = moving_aves

    x_range = []
    for i,_ in enumerate(ord_baseline):
        x_range.append(DIST_BETWEEN_SAMPLES*i)

    first_good = 0
    for i, val in enumerate(deltas_base):
        if val == 0:
            continue
        else:
            first_good = i-1
            break

    avg_baseline_battery = sum(deltas_base)/len(deltas_base)
    #avg_test_battery = sum(get_battery_deltas(ord_test, timewindow=60))/len(ord_test)
    avg_test_battery = 0
    plt.figure()
    plt.subplot(1,2,1)
    plt.title("Battery capacity over time (mW vs time)")
    plt.ylabel("mWh")
    plt.xlabel("Seconds")
    plt.plot(x_range, ord_baseline, label='Capacity')
    axes = plt.gca()
    slope = (ord_baseline[-1] - ord_baseline[0])/(x_range[-1]-x_range[0])
    y_vals = ord_baseline[0] + slope * np.asarray(x_range)
    plt.plot(x_range, y_vals, label='linear capacity (1)')

    slope = (ord_baseline[-1] - ord_baseline[first_good])/(x_range[-1]-x_range[first_good])
    y_vals = ord_baseline[0] + slope * np.asarray(x_range)
    plt.plot(x_range, y_vals, label='linear capacity (2 - ignoring 0s)')
    plt.legend()

    plt.subplot(1,2,2)
    plt.title("Drain rate over time (mW vs time)")
    plt.ylabel("mW")
    plt.xlabel("Seconds")
    plt.plot(x_range[:len(deltas_base)], deltas_base, label='drain rate')
    plt.axhline(avg_baseline_battery, label='mean', color='red')
    plt.legend()
    plt.show()

    avg_baseline_battery = abs(millijoules_to_milliwatts(
        milliwatthours_to_millijoules((ord_baseline[0] - ord_baseline[-1])),
        args['baseline_time']
    ))
    avg_test_battery = abs(millijoules_to_milliwatts(
        milliwatthours_to_millijoules((ord_test[0] - ord_test[-1])),
        args['test_time']
    ))

    # Conduct power usage analysis
    ord_baseline = get_ordered_datalist_power(baselinedata)
    ord_baseline = [r[1:] for r in ord_baseline]

    avg_baseline_consumption = get_avg_consumption_rate(ord_baseline, args['baseline_time'])

    ord_test = get_ordered_datalist_power(testdata)
    ord_test = [r[1:] for r in ord_test]

    avg_test_consumption = get_avg_consumption_rate(ord_test, args['test_time'])
    print(ord_test)

    if args['plot_power']:
        plt.figure()
        ax1 = plt.gca()

        x_range = []
        ignores = []
        for i, _ in enumerate(ord_baseline):
            x_range.append(DIST_BETWEEN_SAMPLES*i)
        for i, val in enumerate(ignores):
            if i == 0:
                ignores.append(i)

        number_of_plots = len(ord_baseline) - len(ignores)
        colormap = plt.cm.nipy_spectral #I suggest to use nipy_spectral, Set1,Paired
        ax1.set_color_cycle([colormap(i) for i in np.linspace(0, 1, number_of_plots)])

        all_entries = [x for x in zip(*ord_baseline)]
        for i, row in enumerate(all_entries):
            if i in ignores: continue
            plt.plot(x_range,[x/60 for x in row], label=header[i+1])
        plt.title("Baseline Power (mW) over time (s)")
        plt.legend()

        plt.figure()
        ax1 = plt.gca()

        x_range = []
        ignores = []
        for i, _ in enumerate(ord_test):
            x_range.append(DIST_BETWEEN_SAMPLES*i)
        for i, val in enumerate(ignores):
            if i == 0:
                ignores.append(i)

        number_of_plots = len(ord_test) - len(ignores)
        colormap = plt.cm.nipy_spectral #I suggest to use nipy_spectral, Set1,Paired
        ax1.set_color_cycle([colormap(i) for i in np.linspace(0, 1, number_of_plots)])

        all_entries = [x for x in zip(*ord_test)]
        for i, row in enumerate(all_entries):
            if i in ignores: continue
            plt.plot(x_range,[x/60 for x in row], label=header[i+1])
        plt.title("Testing Power (mW) over time (s)")
        plt.legend()
        plt.show()

    if otype == 'json':
        return {
            'power': {
                'header': header[1:],
                'avg-baseline (mW)': avg_baseline_consumption,
                'avg-test (mW)': avg_test_consumption
            },
            'battery': {
                'avg-baseline (mW)': avg_baseline_battery,
                'avg-test (mW)': avg_test_battery
            }
        }
    else:
        powerbaseheader = ','.join(['power-baseline-' + i + '-mwh-per-s' for i in header[1:]])
        powertestheader = ','.join(['power-testing-' + i + '-mwh-per-s' for i in header[1:]])
        batteryheader = 'battery-baseline-mwh-per-s,battery-testing-mwh-per-s'
        
        powerbasecsv = powerbaseheader + '\n' + ','.join([str(x) for x in avg_baseline_consumption])
        powertestcsv = powertestheader + '\n' + ','.join([str(x) for x in avg_test_consumption])
        batterycsv = batteryheader + '\n' + ','.join([str(avg_baseline_battery), str(avg_test_battery)])

        return {
            'power-base': powerbasecsv,
            'power-test': powertestcsv,
            'battery': batterycsv
        }


def compare_against_baseline(args):
    if args['data']:
        datadir_abs = os.path.abspath(args['data'])
        baselinedir = os.path.join(datadir_abs, 'baseline')
        testdir = os.path.join(datadir_abs, 'testing')
        resultsdir = os.path.join(datadir_abs, 'results')
        configfile = os.path.join(datadir_abs, 'config.json')
    else:
        baselinedir = os.path.abspath(args['baseline_data'])
        testdir = os.path.abspath(args['test_data'])
        resultsdir = os.path.join(os.getcwd(), 'results')
        configfile = os.path.abspath(args['config_data'])

    otype = args['outputtype']

    with open(configfile, 'r') as f:
        config = json.load(f)

    if not args['baseline_time']:
        try:
            args['baseline_time'] = config['baselineendtime'] - config['baselinestarttime']
            print("Baseline time in seconds: %s" % str(args['baseline_time']))
        except Exception as e:
            print(e)
            print("Error while trying to get start times.")
            config['baselinestarttime'] = config['starttime']
            args['baseline_time'] = 600

    print("Results will be stored in %s" % resultsdir)
    if not os.path.exists(resultsdir):
        os.mkdir(resultsdir)

    print("Comparing data...")
    results = compare_data(baselinedir, testdir, config, args)

    if otype == 'json':
        currtime = str(int(time.time()))
        resultsjson = os.path.join(resultsdir, 'results' + currtime + '.json')

        print("Saving results to %s..." % resultsjson)
        with open(resultsjson, 'w') as f:
            json.dump(results, f)
    else:
        currtime = str(int(time.time()))

        for key in results:
            resultscsv = os.path.join(resultsdir, str(key) + currtime + '.csv')
            
            print("Saving results to %s..." % resultscsv)
            with open(resultscsv, 'w') as f:
                f.write(results[key])

    print("Displaying results...")
    display_results(results, otype)


def main():
    parser = analysisparser()
    args = parser.parse_args()
    args = dict(vars(args))

    if args['compare']:
        compare_against_baseline(args)
    else:
        raise Exception("No analysis specified.")


if __name__=="__main__":
    main()