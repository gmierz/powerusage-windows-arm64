import re
import time
import datetime

from utils import (
    pattern_find,
    get_paths_from_dir,
    millijoules_to_milliwatts
)


def open_srumutil_report(fname, application, excluded_apps):
    with open(fname, 'r') as f:
        rawdata = f.readlines()
        data = []
        for row in rawdata:
            row = row.split('\n')[0]
            data.append(row.split(','))

    header = data[0]
    data = data[1:]

    finaltime = int(time.mktime(
        datetime.datetime.strptime(data[-1][2].lstrip(' ').split('.')[0], "%Y-%m-%d:%H:%M:%S").timetuple()
    ))

    # There's a lot of data - filter as soon as possible
    new_data = []
    for row in data:
        i = 2
        found = False
        while not found:
            try:
                tstamp = row[i].lstrip(' ').split('.')[0]
                utc_tstamp = int(time.mktime(
                    datetime.datetime.strptime(tstamp, "%Y-%m-%d:%H:%M:%S").timetuple()
                ))
                found = True
            except:
                i += 1
                continue

        # Don't gather things from before this files run
        # (specified by starttime in config.json).
        if utc_tstamp < finaltime:
            continue
        # Skip requested apps
        if excluded_apps != None:
            if pattern_find(row[0], excluded_apps):
                continue
        # Get application requested, replace timestamp at the same time
        if pattern_find(row[0], application) or '' in application:
            newval = row[:2]
            newval.append(utc_tstamp)
            newval.extend(row[i:])
            new_data.append(newval)

    return header, new_data


def merge_srum_rows(datadict):
    merged_dict = {}
    for time, data in datadict.items():
        merged_dict[time] = [0 for _ in range(len(data[0]))]
        for row in data:
            merged_dict[time] = [
                merged_dict[time][i] + int(val)
                for i, val in enumerate(row)
            ]
    return merged_dict


def convert_data_to_milliwatts(datadict, total_time):
    new_data = {}
    for time, data in datadict.items():
        new_data[time] = []
        for val in data:
            new_data[time].append(
                millijoules_to_milliwatts(
                    val, total_time
                )
            )
    return new_data


def get_srumutil_files(datadir):
    files = get_paths_from_dir(datadir, file_matchers=['srumutil'])
    return files


def open_srumutil_data(testdir, application, excluded_apps, teststarttim, dist_between_samples):
    files = get_srumutil_files(testdir)

    currdata = {}
    for file in files:
        header, data = open_srumutil_report(file, application, excluded_apps)

        for row in data:
            if str(row[2]) not in currdata:
                currdata[str(row[2])] = []
            currdata[str(row[2])].append([int(x.lstrip(' ')) for x in row[13:]])
            if currdata[str(row[2])][-1][-1] > 1000000:
                currdata[str(row[2])] = currdata[str(row[2])][:-1]

    print(currdata.keys())
    print("Total datapoints found: %s" % len(list(currdata.keys())))

    header = ['timestamp'] + [x.lstrip(' ') for x in header[12:]]
    merged_data = merge_srum_rows(currdata)
    #fmt_data = convert_data_to_milliwatts(merged_data, dist_between_samples)

    #print(fmt_data)

    return header, merged_data

