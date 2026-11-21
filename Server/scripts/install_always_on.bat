@echo off
rem One-time setup: MediGen server starts by itself when you log on to Windows,
rem keeps running in the background, and the PC does not sleep while plugged in.
rem Run this file once on the pharmacy PC or laptop. Keep the charger plugged in.
setlocal
cd /d "%~dp0\.."
set ROOT=%cd%

echo.
echo [1/4] Creating the "MediGen Server" startup task...
schtasks /Create /TN "MediGen Server" /TR "wscript.exe \"%ROOT%\scripts\run_server_hidden.vbs\"" /SC ONLOGON /F
if errorlevel 1 (
  echo FAILED to create the task. Run this file again as Administrator ^(right click ^> Run as administrator^).
  pause
  exit /b 1
)

echo [2/4] Power settings on AC power: no sleep, and closing the lid does nothing...
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0
powercfg /setactive SCHEME_CURRENT

echo [3/4] Checking the MySQL service (it must start with Windows)...
sc query MySQL80 | find "RUNNING" > nul
if errorlevel 1 (
  echo WARNING: MySQL80 service is not running. Open Services, find MySQL80, set Startup type to Automatic and Start it.
) else (
  echo MySQL80 is running.
)

echo [4/4] Starting the server now...
wscript.exe "%ROOT%\scripts\run_server_hidden.vbs"
echo.
echo Done. Open http://127.0.0.1:5000 in a browser to check. The log is in logs\server.log.
pause
