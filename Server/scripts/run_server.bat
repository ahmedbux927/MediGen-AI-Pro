@echo off
rem MediGen server that keeps running: if it stops or crashes, it starts again after 10 seconds.
rem Output goes to logs\server.log. To stop it for good, end the "python" process in Task Manager
rem and then disable the "MediGen Server" task (see scripts\install_always_on.bat).
cd /d "%~dp0\.."
if not exist logs mkdir logs
:loop
echo [%date% %time%] MediGen server starting>> logs\server.log
python app.py>> logs\server.log 2>&1
echo [%date% %time%] MediGen server stopped with code %errorlevel%. Starting again in 10 seconds.>> logs\server.log
ping -n 11 127.0.0.1 > nul
goto loop
