# Power and battery usage monitor for Windows 10 on ARM64

Run `powerusagerunner.bat` from the repo directory with an output directory as the first argument (defaults to the current directory). Prompts will give you instructions on how to proceed. Once complete, pass the output directory to the `powerusageanalyzer.py` with `--data`. 

IMPORTANT: Polling interval should be no less than 1 minute, otherwise you risk duplicating data which is difficult to find and filter.

-------------------------------------------------------------

The following method using python fails intermittently due to 'energy.dll' errors so it is no longer in use, but it is left here as it may be useful in the future or for a different windows OS:

This tool can monitor with `powerusagerunner.py` and then analyze the data with `powerusageanalyzer.py`.
See the scripts for more info on how to use them (or see --help).