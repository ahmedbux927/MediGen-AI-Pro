@echo off
rem v88.00: B10 - stops the MediGen server. The PID is the LAST column of netstat output
rem (the old file used a fixed column, which is wrong when the state column is missing).
rem Use this before you update the files.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "PORT=5000"
if exist ".env" for /f "tokens=2 delims==" %%a in ('findstr /B "APP_PORT=" ".env"') do set "PORT=%%a"
set FOUND=0
for /f "tokens=*" %%L in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  set "PID="
  for %%P in (%%L) do set "PID=%%P"
  if defined PID (
    set FOUND=1
    taskkill /PID !PID! /F >nul 2>&1
  )
)
if "%FOUND%"=="1" (echo MediGen server stopped.) else (echo MediGen server is not running.)
pause
