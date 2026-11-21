@echo off
rem Daily backup for Windows Task Scheduler. Run from anywhere; it finds the project folder itself.
cd /d "%~dp0\.."
python scripts\backup_db.py
exit /b %errorlevel%
