import argparse
import os
import time
import json

from powerusageparser import open_srumutil_data
from batteryusageparser import open_battery_reports
from utils import get_ordered_datalist


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


def get_avg_consumption_rate(ordered_datalist):
	consumption = []
	for row in ordered_datalist:
		consumption.append([
			x/60 for x in row
		])

	avg_consumption = [sum(x)/len(x) for x in zip(*consumption)]
	return avg_consumption


def get_battery_deltas(ordered_datalist, timewindow=60):
	deltas = []
	for i in range(len(ordered_datalist)):
		if i >= len(ordered_datalist) - 1:
			continue
		deltas.append((ordered_datalist[i]-ordered_datalist[i+1])/timewindow)
	return deltas


def compare_data(baselinedir, testdir, config, args):
	app = args['application']
	otype = args['outputtype']

	print("Getting SRUMUTIL baseline data...")
	header, baselinedata = open_srumutil_data(
		baselinedir,
		args['baseline_application'],
		args['exclude_baseline_apps'],
		config['starttime']
	)
	print("Getting SRUMUTIL testing data...")
	_, testdata = open_srumutil_data(
		testdir,
		args['application'],
		args['exclude_test_apps'],
		config['teststarttime']
	)

	print("Getting battery reports for baseline...")
	baseline_reports = open_battery_reports(baselinedir)
	print("Getting battery reports for test...")
	test_reports = open_battery_reports(testdir)

	print("Running comparison")

	# Conduct battery usage analysis
	ord_baseline_battery = get_ordered_datalist(baseline_reports)
	ord_test_battery = get_ordered_datalist(test_reports)

	ord_baseline = [r[1] for r in ord_baseline_battery]
	ord_test = [r[1] for r in ord_test_battery]

	deltas_baseline = get_battery_deltas(ord_baseline)
	deltas_test = get_battery_deltas(ord_test, timewindow=60)

	avg_baseline_battery = sum(deltas_baseline)/len(deltas_baseline)
	avg_test_battery = sum(deltas_test)/len(deltas_test)

	# Conduct power usage analysis
	ord_baseline = get_ordered_datalist(baselinedata)
	ord_baseline = [r[1:] for r in ord_baseline]

	avg_baseline_consumption = get_avg_consumption_rate(ord_baseline)

	ord_test = get_ordered_datalist(testdata)
	ord_test = [r[1:] for r in ord_test]

	avg_test_consumption = get_avg_consumption_rate(ord_test)

	if otype == 'json':
		return {
			'power': {
				'header': header[1:],
				'avg-baseline (mWh/s)': avg_baseline_consumption,
				'avg-test (mWh/s)': avg_test_consumption
			},
			'battery': {
				'avg-baseline (mWh/s)': avg_baseline_battery,
				'avg-test (mWh/s)': avg_test_battery
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

	print("Results will be stored in %s" % resultsdir)
	if not os.path.exists(resultsdir):
		os.mkdir(resultsdir)

	print("Comparing data...")
	results = compare_data(baselinedir, testdir, config, args)

	if otype == 'json':
		currtime = str(int(time.time()))
		resultsjson = os.path.join(resultsdir, 'results' + currtime	+ '.json')

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