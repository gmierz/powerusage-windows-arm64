import io
import argparse
import os
import json
import time
import psutil
import subprocess

from threading import Thread


def powerparser():
	parser = argparse.ArgumentParser(
		description='Continuously poll power usage and battery usage'
					'measurements and save them for post-processing.'
	)

	parser.add_argument('--no-battery-usage', '-nbu', action='store_true', default=False,
						help='If set, battery usage will not be measured (measured by default).')

	parser.add_argument('--no-power-usage', '-npu', action='store_true', default=False,
						help='If set, power usage will not be measured (measured by deafult).')

	parser.add_argument('--no-ram-power-usage', '-nrpu', action='store_true', default=False,
						help='If set, RAM power consumption will not be estimated. This polls much'
						     'more than power and battery usage estimators (once every 5 seconds).' )

	parser.add_argument('--poll-interval', type=float, default=60,
						help='Minimum interval is 1 minute with SRUMUtil from powercfg.exe. If '
							 'there are holes in the data, consider decreasing this interval '
							 '(default is 60 seconds).')

	parser.add_argument('--ram-poll-interval', type=float, default=5,
						help='Interval at which RAM usage should be polled at '
						     '(default is 5 seconds).')

	parser.add_argument('--output', type=str, required=True,
						help='Location to store output.')

	return parser


class SRUMUtilPoller(Thread):
	def __init__(self, args, stopper):
		Thread.__init__(self)
		self.stopper = stopper
		if not args:
			return

		self.powerusage = not args['no_battery_usage']
		self.batteryusage = not args['no_power_usage']
		self.output = args['output']
		self.poll_interval = args['poll_interval']

	def get_curr_file_count(self, filename):
		return len([
			f
			for f in os.listdir(self.output)
			if os.path.isfile(f) and (filename in f or f in filename)
		])

	def run(self):
			while not self.stopper.is_stop_set():
				currtime = str(int(time.time()))
				if self.powerusage:
					# Call powercfg.exe /SRUMUTIL
					retries = 5
					success = False
					while not success and retries >= 0:
						try:
							command = ['powercfg.exe', '/SRUMUTIL', '/CSV', '/OUTPUT']
							command.append('srumutil' + currtime + '.csv')
							subprocess.check_call(command)
							success = True			
						except:
							print('retrying...')
							retries -= 1
							time.sleep(5)
							continue
				if self.batteryusage:
					# Call powercfg.exe /BATTERYREPORT
					command = ['powercfg.exe', '/BATTERYREPORT', '/OUTPUT']
					command.append('batteryreport' + currtime + '.html')
					subprocess.check_call(command)

				if self.stopper.is_stop_set():
					break

				time.sleep(self.poll_interval)


class RAMPoller(Thread):
	def __init__(self, args, stopper):
		Thread.__init__(self)
		self.stopper = stopper
		self.current_memory = 0
		self.rampowerusage = not args['no_ram_power_usage']
		self.output = args['output']
		self.ram_poll_interval = args['ram_poll_interval']

	def get_memory(self):
		tmp = psutil.virtual_memory()
		self.current_memory = tmp.used >> 20
		return self.current_memory

	def get_ram_power_usage(self):
		# Estimated by the usage of 0.1 mW/Gb from
		# here: https://ieeexplore.ieee.org/document/8310256
		# Note that mW signifies Joules/second.
		return (self.current_memory/1024) * 0.1

	def run(self):
		ramfile = os.path.join(self.output, 'ram_usage.csv')
		f = io.open(ramfile, 'w')

		# Write header
		try:
			f.write('CurrentTime,RAMUsage,RAMPowerConsumption\n')

			def write_current_estimates():
				f.write(','.join([
					str(time.time()),
					str(self.get_memory()),
					str(self.get_ram_power_usage())
				]) + '\n')

			write_current_estimates()

			while not self.stopper.is_stop_set():
				if self.rampowerusage:
					# Write them to the file
					print('Writing RAM usage entry...')
					write_current_estimates()
					f.flush()

				if self.stopper.is_stop_set():
					break

				time.sleep(self.ram_poll_interval)
			f.close()
		except:
			f.close()
			raise


class DaemonStopper(object):
	def __init__(self):
		self.stop = False

	def is_stop_set(self):
		return self.stop

	def stop(self):
		self.stop = True

	def reset(self):
		self.stop = False


def main():
	parser = powerparser()
	args = parser.parse_args()
	args = dict(vars(args))

	currdir = os.getcwd()
	outputdir = args['output']

	if not os.path.exists(outputdir):
		os.mkdir(outputdir)

	outputdir = os.path.abspath(outputdir)

	usagedir = os.path.join(outputdir, 'usagerunfrom' + str(int(time.time())))
	baselinedir = os.path.join(usagedir, 'baseline')
	testdir = os.path.join(usagedir, 'test')

	os.mkdir(usagedir)
	os.mkdir(baselinedir)
	os.mkdir(testdir)

	starttime = time.time() - 3600*5
	with open(os.path.join(usagedir, 'config.json'), 'w+') as f:
		json.dump({
			'starttime': starttime,
			'args': args
		}, f)

	# Get the baseline
	print("When ready, press enter to start collecting the baseline.")
	print("It is important to do nothing during this stage to obtain")
	print("baseline data that measures default power consumption.")

	input()

	print("Gathering baseline for 5 minutes...")
	os.chdir(baselinedir)

	args['output'] = baselinedir
	stopper = DaemonStopper()
	runner = SRUMUtilPoller(args, stopper)
	ramrunner = RAMPoller(args, stopper)
	runner.daemon = True
	ramrunner.daemon = True

	try:
		ramrunner.start()
		runner.start()
	except:
		stopper.stop()
		raise
		return

	# Sleep for 5 minutes
	time.sleep(300)

	print("Done gathering baseline. Reseting runner daemons...")

	runner.output = testdir
	ramrunner.output = testdir

	teststarttime = time.time() - 3600*5
	with open(os.path.join(usagedir, 'config.json'), 'w+') as f:
		json.dump({
			'starttime': starttime,
			'teststarttime': teststarttime,
			'args': args
		}, f)

	os.chdir(testdir)
	print("Test gathering started...you may start experiments now.")

	print("Press q/Q to quit the program")

	val = ''
	while val not in ('q', 'Q'):
		try:
			input()
		except Exception as e:
			print(e)
			continue

	print("Stopping...please wait.")
	stopper.stop()

	runner.join()
	RAMRUNNER.join()

	os.chdir(currdir)
	print("Done.")


if __name__=="__main__":
	main()