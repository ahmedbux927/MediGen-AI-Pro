@echo off
rem ============================================================
rem  MediGen AI Pro - build the Windows program (MediGenAIPro.exe)
rem  Run this once on the Windows PC from the project folder:
rem      build_exe.bat
rem  Result: dist\MediGenAIPro\MediGenAIPro.exe
rem  Needs: Python 3.10+ on this PC and internet (for pip).
rem ============================================================
setlocal
cd /d "%~dp0"

if not exist "static\vendor" (
    echo [!] static\vendor is missing. Copy your static\vendor folder back first
    echo     ^(the offline Bootstrap and Chart.js files^), then run this again.
    goto :fail
)

echo [1/4] Installing requirements and PyInstaller...
python -m pip install -r requirements.txt pywebview pyinstaller
if errorlevel 1 goto :fail

echo [2/4] Building MediGenAIPro.exe ...
python -m PyInstaller --noconfirm --clean --onedir --console --name MediGenAIPro ^
    --collect-all docx --collect-all reportlab --collect-all openpyxl --collect-all webview ^
    --icon "assets\medigen.ico" ^
    desktop.py
if errorlevel 1 goto :fail

echo [3/4] Copying the templates, static files and folders next to the program...
xcopy /E /I /Y /Q "templates" "dist\MediGenAIPro\templates" >nul
if errorlevel 1 goto :fail
xcopy /E /I /Y /Q "static" "dist\MediGenAIPro\static" >nul
if errorlevel 1 goto :fail
xcopy /E /I /Y /Q "database" "dist\MediGenAIPro\database" >nul
if errorlevel 1 goto :fail
rem The Settings page runs scripts\backup_db.py and scripts\restore_test.py -
rem they must sit next to the exe or Backup now / Restore test cannot work.
xcopy /E /I /Y /Q "scripts" "dist\MediGenAIPro\scripts" >nul
if errorlevel 1 goto :fail
if exist "dist\MediGenAIPro\scripts\__pycache__" rmdir /S /Q "dist\MediGenAIPro\scripts\__pycache__"
if exist "mysql\bin\mysqld.exe" (
    echo     Copying the bundled MySQL server folder ^(this is large^)...
    xcopy /E /I /Y /Q "mysql" "dist\MediGenAIPro\mysql" >nul
    if errorlevel 1 goto :fail
)
if not exist "dist\MediGenAIPro\backups" mkdir "dist\MediGenAIPro\backups"
if not exist "dist\MediGenAIPro\static\profiles" mkdir "dist\MediGenAIPro\static\profiles"

echo [4/4] Creating .env next to the program (only if it is missing)...
if not exist "dist\MediGenAIPro\.env" (
    if exist ".env" (
        copy /Y ".env" "dist\MediGenAIPro\.env" >nul
    ) else (
        copy /Y ".env.example" "dist\MediGenAIPro\.env" >nul
        echo     [!] Created .env from .env.example. Open dist\MediGenAIPro\.env and set DB_PASSWORD.
    )
)

echo.
echo Done. Start the program with:  dist\MediGenAIPro\MediGenAIPro.exe
echo Keep the whole dist\MediGenAIPro folder together. Do not move the exe alone.
echo.
pause
exit /b 0

:fail
echo.
echo Build failed. Read the messages above, fix the first error, and run build_exe.bat again.
echo Take a screenshot of this window and send it - the first error line is the real cause.
pause
exit /b 1
