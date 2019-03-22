import argparse
import os
import time
import json

from comparisons import compare_data, compare_to_wpa


def analysisparser():
    parser = argparse.ArgumentParser(
        description='Analyze data from a `usagerunfrom<TIME>` folder containing the directories'
                    '`baseline`, and `test`. Analysis performed depends on the flag. Currently '
                    'the only existing analysis is a simple comparison against the baseline.'
    )

    parser.add_argument('--data', type=str, default=None,
                        help='Location of the data (must point to usagerunfrom*).')

    parser.add_argument('--ignore-power', action='store_true', default=False,
                        help="Ignore power SRUMUTIL measurements.")

    parser.add_argument('--time-to-analyze', type=int, default=None,
                        help='Amount of time to analyze.')

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
                        help='Excludes listed applications from power measurements during baseline.')

    parser.add_argument('--exclude-test-apps', nargs='+', default=None,
                        help='Excludes listed applications from power measurements during test.')

    parser.add_argument('--output', type=str, default=os.getcwd(),
                        help='Location to store output.')

    parser.add_argument('--smooth-battery', action='store_true', default=False,
                        help='Type of output to store, can be either `csv` or `json`.')

    parser.add_argument('--plot-power', action='store_true', default=False,
                        help='Plots power usage over time.')

    parser.add_argument('--plot-battery', action='store_true', default=False,
                        help='Plots battery usage over time, drain rates, and the approximate linear drain rate.')

    parser.add_argument('--consumption-from', nargs='+', default=None,
                        help='Only calculates power consumption from these sources (must match values from SRUMUTIL csv header).')

    parser.add_argument('--compare', action='store_true', default=False,
                        help='Compares the baseline data to the test data (defined by the folder names).')

    parser.add_argument('--compare-to-wpa', action='store_true', default=False,
                        help='Compares the data type specified by --wpa-type, to the WPA data specified with this flag.')

    parser.add_argument('--wpa-type', type=str, default='baseline',
                        help='The data type (either baseline, by default, or test) to use in comparison with WPA data.')

    return parser


def display_results(results):
    print()
    for key in results:
        print(key)
        print(results[key])
        print()

    print("Summary of baseline results")
    print("Battery percent-lost: %s" % str(results['battery'].split('\n')[-1].split(',')[4]))
    print("Battery: %s mW, %s mWh" % (
            str(results['battery'].split('\n')[-1].split(',')[0]),
            str(results['battery'].split('\n')[-1].split(',')[2])
        )
    )
    print("Power: %s mW, %s mWh" % (
            str(results['power-base-mw'].split('\n')[-1].split(',')[-1]),
            str(results['power-base-mwh'].split('\n')[-1].split(',')[-1])
        )
    )
    print()

    print("Summary of test results")
    print("Battery percent-lost: %s" % str(results['battery'].split('\n')[-1].split(',')[5]))
    print("Battery: %s mW, %s mWh" % (
            str(results['battery'].split('\n')[-1].split(',')[1]),
            str(results['battery'].split('\n')[-1].split(',')[3])
        )
    )
    print("Power: %s mW, %s mWh" % (
            str(results['power-test-mw'].split('\n')[-1].split(',')[-1]),
            str(results['power-test-mwh'].split('\n')[-1].split(',')[-1])
        )
    )

    return


def display_wpa_results(results):
    return


def do_comparison(args):
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

    with open(configfile, 'r') as f:
        config = json.load(f)

    if not args['baseline_time']:
        try:
            args['baseline_time'] = config['baselineendtime'] - config['baselinestarttime']
            print("Baseline time in seconds: %s" % str(args['baseline_time']))
        except Exception as e:
            print("Error while trying to get baseline start times: %s" % str(e))
            print("Assuming 10 minute length")
            config['baselinestarttime'] = config['starttime']
            args['baseline_time'] = 600

    if not args['test_time']:
        try:
            args['test_time'] = config['teststarttime'] - config['testendtime']
            print("Testing time in seconds: %s" % str(args['baseline_time']))
        except Exception as e:
            print("Error while trying to get testing times: %s" % str(e))
            print("Assuming 10 minute length...")
            args['test_time'] = 600


    print("Results will be stored in %s" % resultsdir)
    if not os.path.exists(resultsdir):
        os.mkdir(resultsdir)

    print("Comparing data...")
    if args['compare']:
        results = compare_data(baselinedir, testdir, config, args)
    elif args['compare_to_wpa']:
        data = baselinedir
        if args['wpa_type'] != 'baseline':
            data = testdir
        results = compare_to_wpa(data, config, args)
    else:
        raise Expection("Missing either --compare, or --compare-to-wpa in arguments.")

    currtime = str(int(time.time()))

    for key in results:
        resultscsv = os.path.join(resultsdir, str(key) + currtime + '.csv')
        
        print("Saving results to %s..." % resultscsv)
        with open(resultscsv, 'w') as f:
            f.write(results[key])

    print("Displaying results...")
    if args['compare']:
        display_results(results)
    elif args['compare_to_wpa']:
        display_wpa_results(results)


def main():
    parser = analysisparser()
    args = parser.parse_args()
    args = dict(vars(args))

    do_comparison(args)


if __name__=="__main__":
    main()