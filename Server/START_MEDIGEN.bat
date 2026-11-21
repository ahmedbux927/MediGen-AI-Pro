@echo off
rem MediGen AI Pro - the ONE start file (v99.00).
rem Finds the MySQL service (MySQL80 / MySQL84 / MySQL90 / MySQL / MariaDB), starts it if
rem needed, starts the MediGen server, waits until it answers, then opens the browser.
rem On any failure this window STAYS OPEN and shows the error - it never just blinks away.
setlocal
title MediGen AI Pro - keep this window open
cd /d "%~dp0"
if not exist logs mkdir logs
set "LOG=logs\startup.log"
echo [%date% %time%] Start requested >> "%LOG%"

if not exist ".env" (
    echo.
    echo  ERROR: The .env file is missing in this folder.
    echo  Copy .env.example to .env and fill in DB_HOST, DB_USER, DB_PASSWORD, DB_NAME.
    echo [%date% %time%] ERROR: .env missing >> "%LOG%"
    echo.
    pause
    exit /b 1
)
for %%K in (DB_HOST DB_USER DB_PASSWORD DB_NAME) do (
    findstr /B /C:"%%K=" ".env" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ERROR: .env is missing the %%K= line. Add it - see .env.example.
        echo [%date% %time%] ERROR: .env missing %%K >> "%LOG%"
        echo.
        pause
        exit /b 1
    )
)

set "SVC="
for %%S in (MySQL80 MySQL84 MySQL90 MySQL MariaDB) do (
    if not defined SVC (
        sc query %%S >nul 2>&1
        if not errorlevel 1 set "SVC=%%S"
    )
)
if not defined SVC (
    echo.
    echo  WARNING: No MySQL service was found (MySQL80, MySQL84, MySQL90, MySQL, MariaDB).
    echo  If MySQL is installed under another name, start it manually, then run this file again.
    echo [%date% %time%] WARNING: no MySQL service found >> "%LOG%"
    echo.
    pause
    exit /b 1
)
sc query %SVC% | find "RUNNING" >nul 2>&1
if errorlevel 1 (
    echo  Starting the %SVC% service...
    net start %SVC% >nul 2>&1
    echo [%date% %time%] %SVC% start requested >> "%LOG%"
)

set "PORT=5000"
for /f "tokens=2 delims==" %%a in ('findstr /B "APP_PORT=" ".env"') do set "PORT=%%a"

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  MediGen is already running. Opening the browser...
    start "" "http://127.0.0.1:%PORT%/"
    exit /b 0
)

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo  Install Python 3.11 or newer and tick "Add to PATH", then run this file again.
    echo.
    pause
    exit /b 1
)

echo  Checking required packages (first time takes a few minutes)...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo.
    echo  ERROR: Package install failed. Check the internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo  Starting the MediGen server...
start "MediGen AI Pro Server" cmd /c "python app.py >> logs\server.log 2>&1"

echo  Waiting for MediGen to be ready...
for /L %%i in (1,1,60) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:%PORT%/api/server/info; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 goto ready
    timeout /t 1 /nobreak >nul
)
echo.
echo  ERROR: MediGen did not start within 60 seconds.
echo  The last lines of logs\server.log are:
echo  ------------------------------------------------
powershell -NoProfile -Command "Get-Content logs\server.log -Tail 20 -ErrorAction SilentlyContinue"
echo  ------------------------------------------------
echo [%date% %time%] ERROR: server did not answer in 60s >> "%LOG%"
echo.
pause
exit /b 1

:ready
echo  MediGen is ready. Opening the browser...
start "" "http://127.0.0.1:%PORT%/"
echo [%date% %time%] Server ready on port %PORT% >> "%LOG%"
exit /b 0
