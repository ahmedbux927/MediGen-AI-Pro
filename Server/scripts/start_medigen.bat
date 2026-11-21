@echo off
rem Starts MediGen AI Pro on this PC only and opens it in the browser.
rem Used by the desktop shortcut that the installer creates.
cd /d "%~dp0\.."
python desktop.py
if errorlevel 1 (
  echo.
  echo MediGen could not start. Read the message above.
  echo Common fixes: check .env (MySQL settings) and run: python -m pip install -r requirements.txt
  pause
)
