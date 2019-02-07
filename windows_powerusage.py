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


'''
Admin rights are required to run powercfg from python. Use runAsAdmin(...) in case it is not.
Check for admin priviledges with isUserAdmin(...).
'''
def isUserAdmin():
    if os.name == 'nt':
        import ctypes
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            traceback.print_exc()
            print "Admin check failed, assuming not an admin."
            return False
    elif os.name == 'posix':
        # Check for root on Posix
        return os.getuid() == 0
    else:
        raise RuntimeError, "Unsupported operating system for this module: %s" % (os.name,)


def runAsAdmin(cmdLine=None, wait=True):
    if os.name != 'nt':
        raise RuntimeError, "This function is only implemented on Windows."

    import win32api, win32con, win32event, win32process
    from win32com.shell.shell import ShellExecuteEx
    from win32com.shell import shellcon

    python_exe = sys.executable

    if cmdLine is None:
        cmdLine = [python_exe] + sys.argv
    elif type(cmdLine) not in (types.TupleType,types.ListType):
        raise ValueError, "cmdLine is not a sequence."
    cmd = '"%s"' % (cmdLine[0],)
    params = " ".join(['"%s"' % (x,) for x in cmdLine[1:]])
    cmdDir = ''
    showCmd = win32con.SW_SHOWNORMAL
    lpVerb = 'runas'  # causes UAC elevation prompt.

    procInfo = ShellExecuteEx(nShow=showCmd,
                              fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                              lpVerb=lpVerb,
                              lpFile=cmd,
                              lpParameters=params)

    if wait:
        procHandle = procInfo['hProcess']    
        obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
        rc = win32process.GetExitCodeProcess(procHandle)
        #print "Process handle %s returned code %s" % (procHandle, rc)
    else:
        rc = None

    return rc


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
    def __init__(self, args, stop_event, kill_event):
        Thread.__init__(self)
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

            if self.powerusage:
                # Call powercfg.exe /SRUMUTIL   
                command = ['powercfg.exe', '/SRUMUTIL', '/CSV', '/OUTPUT']
                command.append(os.path.join(self.output,'srumutil' + currtime + '.csv'))
                with disable_file_system_redirection():
                    if isUserAdmin():
                        subprocess.check_call(command)
                    else:
                        runAsAdmin(command)

            if self.batteryusage:
                # Call powercfg.exe /BATTERYREPORT
                command = ['powercfg.exe', '/BATTERYREPORT', '/OUTPUT']
                command.append(os.path.join(self.output,'batteryreport' + currtime + '.html'))
                with disable_file_system_redirection():
                    subprocess.check_call(command)

            self.stop_event.wait(self.poll_interval)


class WinPowerUsage(object):
    def __init__(self, output):
        self.output = output

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

    def stop(self):
        # Stops gathering data
        self.start_event.clear()
        self.stop_event.set()

    def start(self):
        # Starts gathering data
        self.stop_event.clear()
        self.start_event.set()

    def kill(self):
        # Kills the data gatherer (cannot be restarted afterwards)
        self.kill_event.set()
        self.stop_event.set()
        self.start_event.set()

    def wait(self, timeout):
        self.kill_event.wait(timeout)

    def change_output_loc(newloc):
        # Changing location allows us to run multiple tests
        # without having to restart the runner everytime.
        self.output = output
        self.runner.output = output
