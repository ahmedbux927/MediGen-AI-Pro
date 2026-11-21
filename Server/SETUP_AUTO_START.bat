@echo off
title MediGen - one-time auto start setup
net session >nul 2>&1
if errorlevel 1 (
  echo.
  echo  This file must run as Administrator.
  echo  Right-click it and choose "Run as administrator".
  echo.
  pause
  exit /b 1
)
cd /d "%~dp0"
if not exist ".env" (
  echo  .env is missing in this folder. Create it first, then run this again.
  pause
  exit /b 1
)
echo.
echo  [1/3] MySQL80 will start automatically with Windows...
sc config MySQL80 start= auto
net start MySQL80 >nul 2>&1
echo  [2/3] Opening port 5000 in Windows Firewall (home, public, hotspot)...
netsh advfirewall firewall delete rule name="MediGen 5000" >nul 2>&1
netsh advfirewall firewall add rule name="MediGen 5000" dir=in action=allow protocol=TCP localport=5000 profile=any
echo  [3/3] Creating the hidden auto start task at Windows login...
schtasks /Create /TN "MediGen Server" /TR "wscript.exe //nologo \"%~dp0RUN_SERVER_HIDDEN.vbs\"" /SC ONLOGON /RL HIGHEST /F
echo.
echo  Done. From now on MediGen starts by itself when this PC is turned on and you log in.
echo  Log file: %~dp0logs\autostart.log
echo.
pause
