@echo off
rem ============================================================
rem  MediGen AI Pro - ONE-CLICK Windows app builder
rem  Double-click this file on the Windows PC (inside the Server folder).
rem  Step 1 builds MediGenAIPro.exe (needs Python 3.10+ and internet for pip).
rem  Step 2 builds the single Setup file MediGen_Setup_<version>.exe
rem        (needs Inno Setup 6 - free from https://jrsoftware.org/isinfo.php).
rem  The Setup file runs on any Windows PC - no Python needed there.
rem  MySQL: install MySQL 8 on the target PC, OR put the MySQL 8 ZIP
rem  folder as "mysql" next to this file before building and the Setup
rem  will carry a portable MySQL with it (see installer\README.md).
rem ============================================================
setlocal
cd /d "%~dp0"

echo ===== Step 1 of 2: building MediGenAIPro.exe =====
call build_exe.bat
if errorlevel 1 goto :fail

echo.
echo ===== Step 2 of 2: building the Setup file =====
set "ISCC="
where iscc >nul 2>nul && set "ISCC=iscc"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    echo [!] Inno Setup 6 nahi mila. Step 1 (exe) tayyar hai: dist\MediGenAIPro\
    echo     Setup file ke liye Inno Setup 6 (muft) install karein:
    echo         https://jrsoftware.org/isinfo.php
    echo     Phir yehi file dobara chalain - ya installer\MediGen.iss khol kar Compile dabain.
    pause
    exit /b 0
)
"%ISCC%" "installer\MediGen.iss"
if errorlevel 1 goto :fail
echo.
echo Done. Setup file: dist\MediGen_Setup_*.exe - ye aik file kisi bhi Windows PC par chalegi.
pause
exit /b 0

:fail
echo.
echo Build ruk gaya. Upar ki pehli error parhein, theek karke dobara chalain.
pause
exit /b 1
