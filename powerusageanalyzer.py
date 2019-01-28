import argparse
import os
import time
import json

from powerusageparser import open_srumutil_data, get_ordered_datalist


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

	parser.add_argument('--application', type=str, required=True,
						help='A string that represents the application we should be looking for '
						     'in the given `test` directories `srumuti*.csv` files. i.e. `firefox` '
						     'or `firefox.exe`.')

	parser.add_argument('--baseline-application', type=str, default='',
						help='Same as application, but for the baseline, by default we use power '
						     'usage measurements from all listed applications. As an example, this '
						     'can be used to compare Firefox idling against Firefox displaying '
						     'a full screen video.')

	parser.add_argument('--output', type=str, default=os.getcwd(),
						help='Location to store output.')

	return parser


def display_results(results):
	return


def get_avg_consumption_rate(ordered_datalist):
	consumption = []
	for row in ordered_datalist:
		consumption.append([
			x/60 for x in row # Ignore timestamp
		])

	avg_consumption = [sum(x)/len(x) for x in zip(*consumption)]
	return avg_consumption


def compare_data(baselinedir, testdir, config, args):
	app = args['application']

	header, baselinedata = open_srumutil_data(baselinedir, args['baseline_application'], config['starttime'])
	_, testdata = open_srumutil_data(testdir, args['application'], config['teststarttime'])

	# Get baseline consumption rate
	ord_baseline = get_ordered_datalist(baselinedata)
	ord_baseline = [r[1:] for r in ord_baseline]

	avg_baseline_consumption = get_avg_consumption_rate(ord_baseline)

	ord_test = get_ordered_datalist(testdata)
	ord_test = [r[1:] for r in ord_test]

	avg_test_consumption = get_avg_consumption_rate(ord_test)

	return {
		'header': header[1:],
		'avg-baseline (mWh/s)': avg_baseline_consumption,
		'avg-test (mWh/s)': avg_test_consumption
	}


def compare_against_baseline(args):
	if args['data']:
		datadir_abs = os.path.abspath(args['data'])
		baselinedir = os.path.join(datadir_abs, 'baseline')
		testdir = os.path.join(datadir_abs, 'test')
		resultsdir = os.path.join(datadir_abs, 'results')
		configfile = os.path.join(datadir_abs, 'config.json')
	else:
		baselinedir = os.path.abspath(args['baseline_data'])
		testdir = os.path.abspath(args['test_data'])
		resultsdir = os.path.join(os.getcwd(), 'results')
		configfile = os.path.abspath(args['config_data'])

	with open(configfile, 'r') as f:
		config = json.load(f)

	print("Results will be stored in %s" % resultsdir)
	if not os.path.exists(resultsdir):
		os.mkdir(resultsdir)

	print("Comparing data...")
	results = compare_data(baselinedir, testdir, config, args)

	currtime = str(int(time.time()))
	resultsjson = os.path.join(resultsdir, 'results' + currtime	+ '.json')

	print("Saving results to %s..." % resultsjson)
	with open(resultsjson, 'w') as f:
		json.dump(results, f)

	print("Displaying results...")
	print(results)
	display_results(results)


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