import io
import argparse
import os
import json
import time
import psutil
import subprocess
import sys, traceback, types
import ctypes

from threading import Thread, Event


class disable_file_system_redirection:
    '''
    File System Redirection prevents us from running powercfg
    from 32-bit Python. Disable it with this context manager.
    '''
    _disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
    _revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection
    def __enter__(self):
        self.old_value = ctypes.c_long()
        self.success = self._disable(ctypes.byref(self.old_value))
    def __exit__(self, type, value, traceback):
        if self.success:
            self._revert(self.old_value)


class WinPowerUsageRunner(Thread):
    def __init__(self, args, start_event, stop_event, kill_event):
        Thread.__init__(self)
        self.start_event = start_event
        self.stop_event = stop_event
        self.kill_event = kill_event
        self.powerusage = not args['no_power_usage']
        self.batteryusage = not args['no_battery_usage']
        self.output = args['output']
        self.poll_interval = args['poll_interval']

    def run(self):
        while not self.kill_event.is_set():
            currtime = str(int(time.time()))
            self.start_event.wait()

            self.stop_event.wait(self.poll_interval)
            if self.stop_event.is_set():
                continue

            if self.powerusage:
                # Call powercfg.exe /SRUMUTIL   
                command = ['powercfg.exe', '/SRUMUTIL', '/CSV', '/OUTPUT']
                command.append(os.path.join(self.output,'srumutil' + currtime + '.csv'))
                with disable_file_system_redirection():
                    subprocess.check_call(command)

            if self.batteryusage:
                # Call powercfg.exe /BATTERYREPORT
                command = ['powercfg.exe', '/BATTERYREPORT', '/OUTPUT']
                command.append(os.path.join(self.output,'batteryreport' + currtime + '.html'))
                with disable_file_system_redirection():
                    subprocess.check_call(command)


class WinPowerUsage(object):
    def __init__(self, topdir, output):
        self.topdir = topdir
        self.output = output
        self.current_analysis = None
        self.config = {}

        # The stop event is for waiting 60 seconds,
        # having an event lets us end the sleep.
        self.stop_event = Event()

        # Used to start and pause execution
        self.start_event = Event()

        # Kills the thread entirely
        self.kill_event = Event()

        self.runner = WinPowerUsageRunner(
            args={
                'no_power_usage': False,
                'no_battery_usage': False,
                'output': output,
                'poll_interval': 60
            },
            stop_event=self.stop_event,
            start_event=self.start_event,
            kill_event=self.kill_event
        )
        self.runner.start()

    def log_start(self):
        self.config[self.current_analysis + 'starttime'] = time.time() - 3600*5

    def log_stop(self):
        self.config[self.current_analysis + 'endtime'] = time.time() - 3600*5

    def stop(self):
        # Stops gathering data
        self.log_stop()
        self.start_event.clear()
        self.stop_event.set()

    def baseline_start(self):
        # Starts gathering data
        self.current_analysis = 'baseline'
        self.log_start()
        self.stop_event.clear()
        self.start_event.set()

    def kill(self):
        # Kills the data gatherer (cannot be restarted afterwards)
        self.log_stop()
        self.kill_event.set()
        self.stop_event.set()
        self.start_event.set()
        with open(os.path.join(self.topdir, 'config.json'), 'w')as f:
            json.dump(self.config, f)

    def wait(self, timeout):
        self.kill_event.wait(timeout)

    def change_output_loc(self, newloc):
        # Changing location allows us to run multiple tests
        # without having to restart the runner everytime.
        self.output = newloc
        self.runner.output = newloc

    def test_start(self):
        self.current_analysis = 'test'
        self.log_start()
        self.stop_event.clear()
        self.start_event.set()

