# Power and battery usage monitor for Windows 10 on ARM64

Run `powerusagerunner.bat` from the repo directory with an output directory as the first argument (defaults to the current directory). Prompts will give you instructions on how to proceed. Once complete, pass the output directory to the `powerusageanalyzer.py` with `--data`. 

IMPORTANT: Polling interval should be no less than 1 minute, otherwise you risk duplicating data which is difficult to find and filter.

# Steps to Run

1. Clone this repository.
1. There are a couple ways that the data can be recorded:
	1. Run from `powerusagerunner.bat <BASELINETIME> <TESTINGTIME>`, where `BASELINETIME`, and `TESTINGTIME` must be given in seconds.
	1. Integrate power usage gathering tool into another process with [WinPowerUsage](https://github.com/gmierz/powerusage-windows-arm64/blob/master/windows_powerusage.py#L64-L135) from the file `windows_powerusage.py`.
		1. An example implementation in Raptor can be found in [this bug](https://bugzilla.mozilla.org/show_bug.cgi?id=1525804)
1. Simple experiments should be conducted using the batch file though it can still be easily done with the python version if needed.
1. After running the experiments, an output directory titled `usagerunfrom*` is created and contains the results from the baseline and testing gathering stages.
	1. If running Raptor with this tool, you'll find the data in the `powerusage` folder in the artifact directory.
	1. It's important to call `WinPowerUsage.kill()` when finished to store the config for a more precise analysis.
1. I suggest moving the data off the reference hardware as soon as it's finished to free up the hardware for more tests.
1. Pass the folder to the analyzer like so (the `--data` directory must contain the baseline and testing folders along with a `config.json` file:
   ```
   		python powerusageanalyzer.py --data usagerunfrom1241987128 --compare --application "firefox" --baseline-application "firefox" --plot-power --smooth-battery --baseline-time 21600 --testing-time 600
   ```
   Testing time and baseline time can (most of the time) be found with the values stored in `config.json` and is automatically calculated. If there are issues, it can be changed with the flags in the command above. There are also `--exclude-apps` and `--exclude-baseline-apps` to ignore some applications if needed. See `powerusageanalyzer.py` for more information.