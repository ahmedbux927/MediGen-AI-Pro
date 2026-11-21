@echo off
rem Registers a daily automatic database backup in Windows Task Scheduler (runs at 23:30 every day).
rem Run this file ONCE as Administrator on the shop PC. It uses scripts\backup_db.bat.
set TASK=MediGen_Daily_Backup
schtasks /Create /F /SC DAILY /ST 23:30 /TN "%TASK%" /TR "\"%~dp0backup_db.bat\""
if errorlevel 1 (
  echo Could not create the task. Right-click this file and choose "Run as administrator".
  pause
  exit /b 1
)
echo Daily backup scheduled at 23:30. Check it in Task Scheduler under the name %TASK%.
pause
