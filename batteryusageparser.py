import re

from utils import get_paths_from_dir


def parse_battery_report(fname):
    with open(fname, 'r') as html_file:
        html_lines = html_file.readlines()

    reportLineFound = False
    percentageFound = False

    percentage = 0

    for i, line in enumerate(html_lines):
        if reportLineFound == False:
            matchObj = re.match( r'.*Report generated.*', line)
            if matchObj:
                reportLineFound = True
                continue

        if reportLineFound:
            matchObj = re.match( r'.*"percent">(\d+).*', line)
            if matchObj:
                percentageFound = True
                percentage = matchObj.group(1)
                continue

        if percentageFound:
            matchObj = re.match (r'.*"mw">(.*) mWh.*', line)
            if matchObj:
                capacity = matchObj.group(1)
                capacity = re.sub (r',','', capacity)
                html_file.close()
                return {"battery" : int(percentage), "capacity" : int(capacity)}

    print("Something is wrong with the battery report named %s" % fname)
    return None
