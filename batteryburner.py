import argparse
import os
import time
import numpy as np
import subprocess
import ctypes
import sys

from threading import Thread

from batteryusageparser import parse_battery_report


def powerparser():
	parser = argparse.ArgumentParser(
		description='Continuously poll power usage and battery usage'
					'measurements and save them for post-processing.'
	)

	parser.add_argument('--test-dir', type=str, required=True,
						help='Where the temp battery reports will reside for the burn test.')

	return parser


class Burner(Thread):
	def __init__(self, stopper):
		Thread.__init__(self)
		self.stopper = stopper

	def run(self):
		while not self.stopper.is_stop_set():
			a = np.random.rand(1000000)
			f = np.fft.fft(a)
			np.fft.ifft(f, n=len(a))


class DaemonStopper(object):
	def __init__(self):
		self.stopping = False

	def is_stop_set(self):
		return self.stopping

	def stop(self):
		self.stopping = True


class disable_file_system_redirection:
    _disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
    _revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection
    def __enter__(self):
        self.old_value = ctypes.c_long()
        self.success = self._disable(ctypes.byref(self.old_value))
    def __exit__(self, type, value, traceback):
        if self.success:
            self._revert(self.old_value)


def get_battery_level(test_dir):
	# Call powercfg.exe /BATTERYREPORT
	battery_loc = os.path.join(test_dir, 'batteryreport.html')
	command = ['powercfg.exe', '/BATTERYREPORT', '/OUTPUT']
	command.append(battery_loc)
	with disable_file_system_redirection():
		subprocess.check_call(command)
	return parse_battery_report(battery_loc)


def main():
	parser = powerparser()
	args = parser.parse_args()
	args = dict(vars(args))

	starttime = int(time.time())
	outputdir = args['test_dir']

	tmpdir = os.path.join(outputdir, 'batteryburntmp')
	if not os.path.exists(tmpdir):
		os.mkdir(tmpdir)

	drops_todo = 2
	currlevel = get_battery_level(tmpdir)
	if currlevel['battery'] <= 98:
		print("Battery burn not required.")
		print("Pausing until battery drop detected...")

		detected = False
		while not detected:
			time.sleep(60)
			level = get_battery_level(tmpdir)
			if level['battery'] != currlevel['battery']:
				print("Detected drop, starting recording.")
				detected = True

		sys.exit(0)
	else:
		drops_todo = currlevel['battery'] - 99

	print("Current battery level: %s" % str(currlevel['battery']))
	print("Waiting for %s drops in percentage..." % str(drops_todo))

	# Start up burners
	stopper = DaemonStopper()
	burners = [Burner(stopper) for _ in range(20)]

	for batburn in burners:
		batburn.start()

	prevlevel = currlevel
	while drops_todo > 0:
		time.sleep(60)
		currlevel = get_battery_level(tmpdir)

		if currlevel['battery'] != prevlevel['battery']:
			drops_todo -= 1
			print("Waiting for %s drops in percentage..." % str(drops_todo))

		prevlevel = currlevel

	print("Battery burn done. Stopping the burners...")
	stopper.stop()
	for batburn in burners:
		batburn.join()

	endtime = int(time.time())
	print("Battery burn complete in %s seconds." % str(endtime - starttime))


if __name__=="__main__":
	main()