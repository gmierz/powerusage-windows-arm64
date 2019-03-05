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
        i = 0
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

    return header, new_data, finaltime


def merge_srum_rows(datadict):
    merged_dict = {}
    seen = {}
    for time, data in datadict.items():
        merged_dict[time] = [0 for _ in range(len(data['data'][0]))]
        seen[time] = []
        for row in data['data']:
            if row in seen[time]: continue
            seen[time].append(row)
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


def fill_holes(merged_data, mintime=None, maxtime=None):
    newdata = {}
    if not maxtime:
        maxtime = max(list([int(x) for x in merged_data.keys()]))
    else:
        if str(maxtime) not in merged_data:
            keys = list(merged_data.keys())
            merged_data[str(maxtime)] = [0 for _ in merged_data[keys[0]]]
    if mintime:
        if str(mintime) not in merged_data:
            keys = list(merged_data.keys())
            merged_data[str(mintime)] = [0 for _ in merged_data[keys[0]]]

    for key, val in merged_data.items():
        newdata[str(key)] = val
        newkey = int(key) + 60
        if str(newkey) in merged_data:
            continue
        if newkey > maxtime:
            continue
        while str(newkey) not in merged_data and newkey < maxtime:
            newdata[str(newkey)] = [0 for _ in val]
            newkey = newkey + 60

    return newdata


def open_srumutil_data(testdir, application, excluded_apps, teststarttim, dist_between_samples):
    files = get_srumutil_files(testdir)

    mintime = 0
    maxtime = 0
    currtime = 0
    currdata = {}
    for i, file in enumerate(files):
        header, data, currtime = open_srumutil_report(file, application, excluded_apps)
        if i == 0:
            mintime = currtime
            maxtime = currtime
        elif currtime < mintime:
            mintime = currtime
        elif currtime > maxtime:
            maxtime = currtime

        for row in data:
            if str(row[2]) not in currdata:
                currdata[str(row[2])] = {
                    'data': [],
                    'file': file
                }
            if currdata[str(row[2])]['file'] != file:
                continue
            currdata[str(row[2])]['data'].append([int(x.lstrip(' ')) for x in row[13:]])

    print("Total datapoints found: %s" % len(list(currdata.keys())))

    if len(list(currdata.keys())) == 0:
        return header, currdata

    header = ['timestamp'] + [x.lstrip(' ') for x in header[12:]]
    merged_data = merge_srum_rows(currdata)
    filled_data = fill_holes(merged_data, mintime=mintime, maxtime=maxtime)

    return header, filled_data

