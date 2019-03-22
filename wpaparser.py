import os
import re
import time
import datetime
import csv
import numpy as np

from utils import (
    get_paths_from_dir,
    pattern_find
)

KNOWN_TABLES = [
    'Processes_Summary_Table_Lifetime_By_Process.',
    'Disk_Usage_Utilization_by_Process,_Path_Name,_Stack',
    'CPU_Usage_(Precise)_Utilization_by_Process,_Thread.'
]


def open_wpa_csv(wpa_csv):
    with open(wpa_csv, 'r') as csvfile:
        print("Opening")
        rdr = csv.reader(csvfile, delimiter=',')
        print("Opened")

        header = []
        data = []
        for i, row in enumerate(rdr):
            if i == 0:
                header = row
                continue
            data.append(row)

    return header, data


def get_borders(command_file, testtime):
    header, data = open_wpa_csv(command_file)

    datmat = np.asmatrix(data)
    names = datmat[:, 5]
    start_times = datmat[:, 6]
    end_times = datmat[:, 7]

    starttime = None
    endtime = None
    for i, command in enumerate(names):
        if 'wpr.exe -start' in command[0,0]:
            starttime = float(end_times[i,0])
        elif 'wpr.exe' in command[0,0] and 'stop-' in command[0,0]:
            endtime = float(start_times[i,0])
    if not endtime and not starttime:
        print(
            "Cannot find markers expect huge errors in synchronization (>20s)"
        )
    if not endtime:
        print(
            "Warning, can't find where the test end missing stop-test marker"
        )
        endtime = starttime + testtime
    elif not starttime:
        print(
            "Warning, can't find the start time"
        )
        starttime = endtime - testtime

    return starttime, endtime


def get_wpa_data(testdir, apps, excluded_apps, testtime):
    print("Getting WPA data...")
    files = get_paths_from_dir(os.path.join(testdir, 'etl-data'), file_matchers=KNOWN_TABLES)

    for file in files:
        command_file = pattern_find(file, ['Processes_Summary_Table_Lifetime_By_Process'])
        if command_file:
            command_file = file
            break

    files = list(set(files) - set([command_file]))
    starttime, endtime = get_borders(command_file, testtime)
    print("Start time: {}, End time: {}".format(str(starttime), str(endtime)))

    currdata = {}
    for i, file in enumerate(files):
        print("Processing {}...".format(str(file)))
        header, data = open_wpa_csv(file)

        name = ''
        for table in KNOWN_TABLES:
            if pattern_find(file, [table]):
                name = table
                break

        # Expecting times as the first column, and 
        # data as the second column
        times = [float(t[0,0].replace(',', '')) for t in np.asmatrix(data)[:,0]]
        data = [float(d[0,0].replace(',', '')) for d in np.asmatrix(data)[:,1]]
        if times[0] < starttime:
            first_ind = 0
            for i, t in enumerate(times):
                if t < starttime:
                    continue
                else:
                    first_ind = i
                    break
            times = times[first_ind:]
            data = data[first_ind:]
        if times[-1] > endtime:
            last_ind = len(times) - 1
            for i, t in enumerate(times):
                if t < endtime:
                    continue
                else:
                    last_ind = i
                    break
            times = times[:last_ind+1]
            data = data[:last_ind+1]

        xvals = np.arange(0, endtime-starttime, 1/60)
        currdata[name] = {
            'times': xvals,
            'data': list(np.interp(xvals, times, data)),
            'srate': 60
        }

    print("Total datapoints found: %s" % len(list(currdata.keys())))

    return header, currdata
