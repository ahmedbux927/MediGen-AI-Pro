# How to close the MediGen project (handover)

## 1. Final checks on the shop PC
1. Start the server and log in as Admin.
2. Run `python tests\run_all.py` (expect 1051 passed, 0 failed) and `python tests\run_all.py --live`.
3. Check each item in docs\PROJECT_STATUS.md, sections 2 (A to J), and tick the ones that passed.
4. Make one backup: `scripts\backup_db.bat`, and check the new file in `backups`.

## 2. Save the final copy
- Keep the folder with the current `.env`, `backups` and `static\vendor` in a safe place (for example a USB drive).
- Keep the last zip (MediGen_FULL_v41.zip) as the release copy.
- Do not share `.env`: it holds the database password.

## 3. Stop the server
- If it runs from the always-on task: open Task Manager, end `python.exe` (or `pythonw.exe`), and close any `run_server.bat` window.
- To stop the always-on task completely: open Task Scheduler, find "MediGen Server", and disable it (or delete it).
- To stop the internet link: close the `start_internet.bat` window.

## 4. Optional: stop the PC from sleeping only if needed
- The installer already sets "never sleep" while plugged in. If you want the normal setting back, change it in Power Options.

## 5. Handover to the owner
- Show the Dashboard, a sale, a return, a report and the Word export.
- Give the admin password to the owner only, and change the database root password (see docs\DB_USER_SETUP.md).
- Tell them how to back up and where the backups are.

## 6. What is still open (next phase, needs choices)
- Dark mode, tile home screen, user settings for phone unlock, app settings page, stable internet domain.
