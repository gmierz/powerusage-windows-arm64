:: Runs the power usage estimator
:: OUTPUT_DIR must be given as the first argument
@echo off

echo This batch script must be run from the repo directory.
echo i.e. the current working directory must be ...\powerusage-windows-arm64
echo 

set /p DUMMY=Press ENTER to start baseline collection...

:: Directory variables
set OUTPUT_DIR=%1
set TOOL_DIR=%cd%

:: Baseline variables
set BASELINEINTERVAL=60
set MAXBASELINETIME=600

:: Test variables
set TESTINTERVAL=60
set MAXTESTTIME=900


:: Setup directories
cd %OUTPUT_DIR%
FOR /F %%I IN ('getUTime.bat') DO SET CURRTIME=%%I

set USAGERUNDIR="usagerun%CURRTIME%"
mkdir %USAGERUNDIR%
cd %USAGERUNDIR%

set STARTTIME=%CURRTIME%

set USAGERUNDIR=%cd%
set BASELINEDIR="%USAGERUNDIR%\baseline"
set TESTINGDIR="%USAGERUNDIR%\testing"

mkdir %BASELINEDIR%
mkdir %TESTINGDIR%


:: Start experiment with baseline collection
echo Collecting baseline...
cd %BASELINEDIR%

set BASELINECOUNT=0

:baselineloop
FOR /F %%I IN ('%TOOL_DIR%\getUtime.bat') DO SET CURRTIME=%%I

timeout %BASELINEINTERVAL%

powercfg.exe /batteryreport /output "batteryreport%CURRTIME%.html"
powercfg.exe /srumutil /csv /output "srumutil%CURRTIME%.csv"

set /a "BASELINECOUNT=%BASELINECOUNT%+%BASELINEINTERVAL%"

if %BASELINECOUNT% LSS %MAXBASELINETIME% goto baselineloop
echo Completed baseline collection.


:: Start experiment with test collection
echo Starting testing, press ENTER when ready.
set /p DUMMY=ENTER to continue...
cd %TESTINGDIR%

FOR /F %%I IN ('%TOOL_DIR%\getUtime.bat') DO SET CURRTIME=%%I
set TESTSTARTTIME=%CURRTIME%

set TESTCOUNT=0

:testloop
FOR /F %%I IN ('%TOOL_DIR%\getUtime.bat') DO SET CURRTIME=%%I

timeout %TESTINTERVAL%

powercfg.exe /batteryreport /output "batteryreport%CURRTIME%.html"
powercfg.exe /srumutil /csv /output "srumutil%CURRTIME%.csv"

set /a "TESTCOUNT=%TESTCOUNT%+%TESTINTERVAL%"

if %TESTCOUNT% LSS %MAXTESTTIME% goto testloop

cd %USAGERUNDIR%
echo Storing start time config in %USAGERUNDIR%
echo {"starttime": %STARTTIME%, "teststarttime": %TESTSTARTTIME%} >> config.json

cd %TOOL_DIR%