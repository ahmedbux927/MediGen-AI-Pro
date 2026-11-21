# Keep the MediGen server running all the time

MediGen runs on your PC. The phones and the browsers connect to that PC. So the server runs only while the PC is on, awake, and connected to the network. These steps make the PC do that without you doing anything.

## One-time setup (5 minutes)

1. Keep the laptop plugged into the charger. The power settings below apply only when plugged in.
2. Open the project folder and double click `scripts\install_always_on.bat`.
   - If it says FAILED, right click the file and choose **Run as administrator**.
   - It creates the "MediGen Server" startup task, sets the power options, checks the MySQL service, and starts the server.
3. Restart the laptop once and check that the server comes up by itself after you log on.

## What happens after that

- The server starts when you log on to Windows. There is no window; it runs in the background.
- If the app stops or crashes, it starts again after 10 seconds.
- Every start and stop is written to `logs\server.log`.
- With the lid closed on the charger, the laptop keeps running. Closing the lid on battery still sleeps it (the battery is not changed).

## Check that it is running

- Open `http://127.0.0.1:5000` in a browser on the PC. The login page should open.
- Look at the end of `logs\server.log`. The last line should be a "starting" line with no "stopped" line after it.

## Stop it on purpose

1. Open Task Manager and end the `python.exe` process that runs `app.py`. It restarts after 10 seconds, so end the task first.
2. Open Task Scheduler, find "MediGen Server", and right click > Disable.

## Things that still stop the server

- The laptop is shut down, out of charge, or the power cut has no backup. A small UPS (battery backup for the PC) helps a lot in Pakistan's power cuts.
- Windows restarts for an update. After a restart, the server starts again only after you log on. To avoid being stuck, set Windows Update **Active hours** to cover shop hours.
- MySQL is not running. The install script warns about this.
- The PC is on a different WiFi, or the firewall rule (port 5000, Private network) is missing.

## If you want the server to run without a laptop

A laptop is not built to run 24 hours a day. For a shop that needs the system all day with no interruption, a small dedicated PC that stays on is a better choice. For access from outside the shop (internet), the app needs HTTPS and more security first; do not open port 5000 to the internet as it is.
