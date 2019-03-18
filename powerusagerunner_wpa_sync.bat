:: Runs the power usage estimator
:: OUTPUT_DIR must be given as the first argument
@echo off

echo This batch script must be run from the repo directory.
echo i.e. the current working directory must be ...\powerusage-windows-arm64
echo 

:: Directory variables
set OUTPUT_DIR=%cd%
set TOOL_DIR=%cd%

:: Baseline variables
set BASELINEINTERVAL=60
set MAXBASELINETIME=%1

:: Test variables
set TESTINTERVAL=60
set MAXTESTTIME=%2

:: If testing on AC, it must be specified as the third argument
set ACPOWER=%3

cd %OUTPUT_DIR%
FOR /F %%I IN ('getUTime.bat') DO SET CURRTIME=%%I

set USAGERUNDIR="usagerun%CURRTIME%"
mkdir %USAGERUNDIR%

if not defined ACPOWER (
	:: Perform battery-burn pre-test (if required)
	python.exe %TOOL_DIR%/batteryburner.py --test-dir %USAGERUNDIR%
) else (
	echo Running on AC Power, no battery drains will be detected.
)

cd %USAGERUNDIR%

set BASELINESTARTTIME=%CURRTIME%

set USAGERUNDIR=%cd%
set BASELINEDIR="%USAGERUNDIR%\baseline"
set TESTINGDIR="%USAGERUNDIR%\testing"

mkdir %BASELINEDIR%
mkdir %TESTINGDIR%

set /p DUMMY=Press ENTER to start baseline collection...

if not defined ACPOWER (
	:: Wait for a percentage drop before starting
	python.exe %TOOL_DIR%/batteryburner.py --test-dir %USAGERUNDIR% --single-drop
)

:: Start experiment with baseline collection
cd %BASELINEDIR%

echo Starting WPA...
wpr.exe -start "Power"
wpr.exe -marker "start-baseline"

echo Collecting baseline...
set BASELINECOUNT=0

:baselineloop
FOR /F %%I IN ('%TOOL_DIR%\getUtime.bat') DO SET CURRTIME=%%I

timeout %BASELINEINTERVAL%

powercfg.exe /batteryreport /output "batteryreport%CURRTIME%.html"
powercfg.exe /srumutil /csv /output "srumutil%CURRTIME%.csv"

set /a "BASELINECOUNT=%BASELINECOUNT%+%BASELINEINTERVAL%"

if %BASELINECOUNT% LSS %MAXBASELINETIME% goto baselineloop
echo Completed baseline collection.

set BASELINEENDTIME=%CURRTIME%

wpr.exe -marker "stop-baseline"
wpr.exe -stop baseline.etl

:: Start experiment with test collection
echo Starting testing, press ENTER when ready.
set /p DUMMY=ENTER to continue...
cd %TESTINGDIR%

echo Starting WPA...
wpr.exe -start "Power"
wpr.exe -marker "start-test"

FOR /F %%I IN ('%TOOL_DIR%\getUtime.bat') DO SET CURRTIME=%%I
set TESTSTARTTIME=%CURRTIME%

echo Starting test collection...
set TESTCOUNT=0

:testloop
FOR /F %%I IN ('%TOOL_DIR%\getUtime.bat') DO SET CURRTIME=%%I

timeout %TESTINTERVAL%

powercfg.exe /batteryreport /output "batteryreport%CURRTIME%.html"
powercfg.exe /srumutil /csv /output "srumutil%CURRTIME%.csv"

set /a "TESTCOUNT=%TESTCOUNT%+%TESTINTERVAL%"

if %TESTCOUNT% LSS %MAXTESTTIME% goto testloop
set TESTENDTIME=%CURRTIME%

wpr.exe -marker "stop-test"
wpr.exe -stop test.etl

cd %USAGERUNDIR%
echo Storing start time config in %USAGERUNDIR%
echo {"baselinestarttime": %BASELINESTARTTIME%, "baselineendtime": %BASELINEENDTIME%, "teststarttime": %TESTSTARTTIME%, "testendtime": %TESTENDTIME%} >> config.json

cd %TOOL_DIR%