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


def get_avg_consumption_rate(ordered_datalist, total_time, milliwatthour=False, header=None, consumption_from=None):
    consumption = []
    for row in ordered_datalist:
        consumption.append([
            x for i, x in enumerate(row) if (not consumption_from) or (header[i] in consumption_from)
        ])

    if milliwatthour:
        avg_consumption = [sum(x)/3600 for x in zip(*consumption)]
    else:
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


def cut_time_out(data, start_ind=0, time_to_analyze=None, interval=60):
    if not time_to_analyze:
        return data

    newdata = data[:start_ind]
    currtime = 0
    for val in data[start_ind:]:
        if currtime >= time_to_analyze:
            break
        newdata.append(val)
        currtime += interval

    return newdata


def compare_data(baselinedir, testdir, config, args):
    app = args['application']

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

    ord_baseline = [float(r[1][1]) for r in ord_baseline_battery]
    ord_test = [float(r[1][1]) for r in ord_test_battery]
    ord_baseline_pc = [float(r[1][0]) for r in ord_baseline_battery]
    ord_test_pc = [float(r[1][0]) for r in ord_test_battery]

    x_range = []
    for i,_ in enumerate(ord_baseline):
        x_range.append(DIST_BETWEEN_SAMPLES*i)

    if args['smooth_battery']:
        N = 20
        cumsum, moving_aves = [0], []

        for i, x in enumerate(ord_baseline, 1):
            cumsum.append(cumsum[i-1] + x)
            if i>=N:
                moving_ave = (cumsum[i] - cumsum[i-N])/N
                moving_aves.append(moving_ave)

        ord_baseline = moving_aves

    deltas_base = get_battery_deltas(ord_baseline, timewindow=60)
    deltas_test = get_battery_deltas(ord_test, timewindow=60)

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

    # Determine baseline boundaries
    found_decrease = 0
    first_good_base = 0
    for i, val in enumerate(deltas_base):
        if val <= 0:
            continue
        else:
            first_good_base = i
            if first_good_base < 0:
                first_good_base = 0
            break

    if args['time_to_analyze']:
        deltas_base = cut_time_out(
            deltas_base, start_ind=first_good_base, time_to_analyze=args['time_to_analyze']
        )
        ord_baseline = cut_time_out(
            ord_baseline, start_ind=first_good_base, time_to_analyze=args['time_to_analyze']
        )

    currmax = max(ord_baseline)
    final_decrease = 0
    decreases = 0
    curr_ind = 0
    all_decreases = []
    while curr_ind < len(ord_baseline):
        for i, val in enumerate(ord_baseline[curr_ind:], curr_ind):
            if val == currmax:
                continue
            else:
                final_decrease_baseline = i
                break
        print(curr_ind)
        print(len(ord_baseline))
        curr_ind = final_decrease_baseline
        if len(all_decreases) == 0:
            all_decreases.append(final_decrease_baseline)
            continue
        if final_decrease_baseline != all_decreases[-1]:
            all_decreases.append(final_decrease_baseline)
        else:
            break

    curr_max = max(ord_baseline)
    all_decreases = [0]
    for i, val in enumerate(ord_baseline):
        if val == curr_max:
            continue
        else:
            curr_max = val
            all_decreases.append(i)

    for i, val in enumerate(all_decreases[:-1]):
        baseline_time = x_range[all_decreases[i+1]]-x_range[val]
        avg_baseline_battery_mw = abs(millijoules_to_milliwatts(
            milliwatthours_to_millijoules((ord_baseline[val] - ord_baseline[all_decreases[i+1]])),
            abs(baseline_time)
        ))
        print(avg_baseline_battery_mw)


    print(all_decreases)
    print("all_decreases")

    currmin = ord_baseline[-1]
    final_decrease = 0
    for i, val in enumerate(ord_baseline[::-1]):
        if val == currmin:
            continue
        else:
            final_decrease = i
            if final_decrease > len(ord_baseline):
                final_decrease = len(ord_baseline)
            else:
                final_decrease_baseline = len(ord_baseline) - final_decrease
            break

    # Determine test boundaries
    found_decrease = 0
    first_good_test = 0
    for i, val in enumerate(deltas_test):
        if val <= 0:
            continue
        else:
            first_good_test = i-1
            if first_good_test < 0 or first_good_test >= len(deltas_test):
                first_good_test = 0
            break

    if args['time_to_analyze']:
        deltas_test = cut_time_out(
            deltas_test, start_ind=first_good_test, time_to_analyze=args['time_to_analyze']
        )
        ord_test = cut_time_out(
            ord_test, start_ind=first_good_test, time_to_analyze=args['time_to_analyze']
        )
    
    currmin = ord_test[-1]
    final_decrease_test = 0
    for i, val in enumerate(ord_test[::-1]):
        if val == currmin:
            continue
        else:
            final_decrease = i
            if final_decrease > len(ord_test):
                final_decrease = len(ord_test)
            else:
                final_decrease_test = len(ord_test) - final_decrease_test
            break


    baseline_time = x_range[final_decrease_baseline]-x_range[first_good_base+1]
    avg_baseline_battery_mw = 0
    if baseline_time > 0:
        avg_baseline_battery_mw = abs(millijoules_to_milliwatts(
            milliwatthours_to_millijoules((ord_baseline[first_good_base+1] - ord_baseline[final_decrease_baseline])),
            abs(baseline_time)
        ))

    test_time = x_range[final_decrease_test]-x_range[first_good_test]
    avg_test_battery_mw = 0
    if test_time > 0:
        avg_test_battery_mw = abs(millijoules_to_milliwatts(
            milliwatthours_to_millijoules((ord_test[first_good_test] - ord_test[final_decrease_test])),
            abs(test_time)
        ))

    avg_baseline_battery_mwh = (ord_baseline[first_good_base] - ord_baseline[-1])
    avg_test_battery_mwh = (ord_test[first_good_test] - ord_test[-1])

    if args['time_to_analyze']:
        ord_baseline_pc = cut_time_out(ord_baseline_pc, start_ind=first_good_base, time_to_analyze=args['time_to_analyze'])
        ord_test_pc = cut_time_out(ord_test_pc, start_ind=first_good_base, time_to_analyze=args['time_to_analyze'])

    pc_lost_base = ord_baseline_pc[first_good_base] - ord_baseline_pc[-1]
    pc_lost_test = ord_test_pc[first_good_test] - ord_test_pc[-1]

    if args['plot_battery']:
        avg_test_battery = 0
        plt.figure()
        plt.subplot(1,2,1)
        plt.title("Battery capacity over time (mW vs time)")
        plt.ylabel("mWh")
        plt.xlabel("Seconds")
        plt.plot(x_range[:len(ord_baseline)], ord_baseline, label='Capacity')
        axes = plt.gca()
        slope = (ord_baseline[-1] - ord_baseline[0])/(x_range[-1]-x_range[0])
        y_vals = ord_baseline[0] + slope * np.asarray(x_range[:len(ord_baseline)])
        plt.plot(list(np.asarray(x_range[:len(ord_baseline)]) + x_range[first_good_base]), y_vals, label='linear capacity (1)')

        slope = (ord_baseline[-1] - ord_baseline[first_good_base])/(x_range[-1]-x_range[first_good_base])
        y_vals = ord_baseline[first_good_base] + slope * (np.asarray(x_range[:len(ord_baseline)]))
        plt.plot(list(np.asarray(x_range[:len(ord_baseline)]) + x_range[first_good_base]), y_vals, label='linear capacity (2 - ignoring 0s)')

        slope = (ord_baseline[final_decrease_baseline] - ord_baseline[first_good_base+1])/(x_range[final_decrease_baseline]-x_range[first_good_base+1])
        y_vals = ord_baseline[first_good_base+1] + slope * (np.asarray(x_range[:len(ord_baseline)]))
        plt.plot(list(np.asarray(x_range[:len(ord_baseline)]) + x_range[first_good_base+1]), y_vals, label='linear capacity (3 - ignoring 0s, and first drain)')

        plt.legend()

        plt.subplot(1,2,2)
        plt.title("Drain rate over time (mW vs time)")
        plt.ylabel("mW")
        plt.xlabel("Seconds")
        plt.plot(x_range[:len(deltas_base)], deltas_base, label='drain rate')
        plt.axhline(avg_baseline_battery_mw, label='mean', color='red')
        plt.legend()
        plt.show()

    # Conduct power usage analysis
    ord_baseline = get_ordered_datalist_power(baselinedata)
    ord_baseline = [r[1:] for r in ord_baseline]

    if args['time_to_analyze']:
        ord_baseline = cut_time_out(ord_baseline, time_to_analyze=args['time_to_analyze'])
        args['baseline_time'] = args['time_to_analyze']

    avg_baseline_consumption_mw = get_avg_consumption_rate(
        ord_baseline, args['baseline_time'], milliwatthour=False, header=header[1:], consumption_from=args['consumption_from']
    )
    avg_baseline_consumption_mwh = get_avg_consumption_rate(
        ord_baseline, args['baseline_time'], milliwatthour=True, header=header[1:], consumption_from=args['consumption_from']
    )

    ord_test = get_ordered_datalist_power(testdata)
    ord_test = [r[1:] for r in ord_test]

    if args['time_to_analyze']:
        ord_test = cut_time_out(ord_test, time_to_analyze=args['time_to_analyze'])
        args['test_time'] = args['time_to_analyze']

    avg_test_consumption_mw = get_avg_consumption_rate(
        ord_test, args['test_time'], milliwatthour=False, header=header[1:], consumption_from=args['consumption_from']
    )
    avg_test_consumption_mwh = get_avg_consumption_rate(
        ord_test, args['test_time'], milliwatthour=True, header=header[1:], consumption_from=args['consumption_from']
    )
    colors = [
        'black', 'silver', 'red', 'gold',
        'darkgreen', 'navy', 'm', 'darkmagenta',
        'mediumslateblue', 'limegreen', 'goldenrod',
        'maroon', 'dimgray'
    ]

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
        colormap = plt.cm.gnuplot
        ax1.set_color_cycle([colormap(i) for i in np.linspace(0, 1, number_of_plots)])

        all_entries = [x for x in zip(*ord_baseline)]

        for i, row in enumerate(all_entries):
            if i in ignores: continue
            plt.plot(x_range,[x/60 for x in row], label=header[i+1], color=colors[i])
        plt.title("Baseline Power (mW) over time (s)")
        plt.legend()
        plt.xlim(0,9500)

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
        colormap = plt.cm.tab20
        ax1.set_color_cycle([colormap(i) for i in np.linspace(0, 1, number_of_plots)])

        all_entries = [x for x in zip(*ord_test)]
        for i, row in enumerate(all_entries):
            if i in ignores: continue
            plt.plot(x_range,[x/60 for x in row], label=header[i+1], color=colors[i])
        plt.title("Testing Power (mW) over time (s)")
        plt.legend()
        plt.show()

    powerbaseheader_mw = ','.join(['power-baseline-' + i + '-mw' for i in header[1:]])
    powertestheader_mw = ','.join(['power-testing-' + i + '-mw' for i in header[1:]])

    powerbaseheader_mwh = ','.join(['power-baseline-' + i + '-mwh' for i in header[1:]])
    powertestheader_mwh = ','.join(['power-testing-' + i + '-mwh' for i in header[1:]])

    batteryheader = 'battery-baseline-mw,battery-testing-mw,' + \
        'battery-baseline-mwh,battery-testing-mwh,' + \
        'battery-baseline-%lost,battery-testing-%lost'

    powerbasecsv = powerbaseheader_mw + '\n' + ','.join([str(x) for x in avg_baseline_consumption_mw])
    powertestcsv = powertestheader_mw + '\n' + ','.join([str(x) for x in avg_test_consumption_mw])

    powerbasecsv_mwh = powerbaseheader_mwh + '\n' + ','.join([str(x) for x in avg_baseline_consumption_mwh])
    powertestcsv_mwh = powertestheader_mwh + '\n' + ','.join([str(x) for x in avg_test_consumption_mwh])

    batterycsv = batteryheader + '\n' + ','.join(
        [
            str(avg_baseline_battery_mw), str(avg_test_battery_mw),
            str(avg_baseline_battery_mwh), str(avg_test_battery_mwh),
            str(pc_lost_base), str(pc_lost_test)
        ]
    )

    return {
        'power-base-mw': powerbasecsv,
        'power-test-mw': powertestcsv,
        'power-base-mwh': powerbasecsv_mwh,
        'power-test-mwh': powertestcsv_mwh,
        'battery': batterycsv
    }


def compare_to_wpa(datadir, wpadir, config, args):
    return None
