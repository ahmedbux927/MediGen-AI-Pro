@echo off
rem v89.00: E8 - one-click desktop start (the recommended option).
rem Starts the server if needed, waits until it answers, then opens the workbench
rem in the default browser. The browser was chosen over a native window because it
rem needs no extra install, is covered by all tests, and prints receipts correctly.
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set "PORT=5000"
if exist ".env" for /f "tokens=2 delims==" %%a in ('findstr /B "APP_PORT=" ".env"') do set "PORT=%%a"

netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul 2>&1
if errorlevel 1 (
    echo  Starting MediGen server...
    start "MediGen AI Pro Server" /min cmd /c "python app.py >> logs\server.log 2>&1"
) else (
    echo  MediGen server is already running.
)

echo  Waiting for MediGen to be ready...
for /L %%i in (1,1,60) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:%PORT%/api/server/info; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 goto ready
    timeout /t 1 /nobreak >nul
)
echo.
echo  MediGen did not start within 60 seconds. See logs\server.log and logs\medigen.log.
pause
exit /b 1

:ready
echo  MediGen is ready. Opening the workbench...
start "" "http://127.0.0.1:%PORT%/"
exit /b 0
