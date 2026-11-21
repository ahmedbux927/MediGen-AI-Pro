@echo off
rem Makes MediGen reachable from the internet (mobile data, other WiFi) through a temporary https address.
rem The MediGen server must already be running. cloudflared is needed once:
rem   winget install --id Cloudflare.cloudflared
setlocal
cd /d "%~dp0\.."
where cloudflared >nul 2>&1
if errorlevel 1 (
  echo cloudflared is not installed.
  echo Open PowerShell and run:  winget install --id Cloudflare.cloudflared
  echo Then close this window and run this file again.
  pause
  exit /b 1
)
echo.
echo MediGen internet access is starting for http://127.0.0.1:5000
echo Wait a few seconds. Find the line with "https://" and ending in trycloudflare.com
echo Type that whole https address in the MediGen app (or open it in any browser).
echo Keep this window open. Closing it stops the internet link.
echo.
cloudflared tunnel --url http://127.0.0.1:5000
echo.
echo The internet link has stopped.
pause
