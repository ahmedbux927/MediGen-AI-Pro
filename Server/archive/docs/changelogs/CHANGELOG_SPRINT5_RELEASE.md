# Sprint 5 - Windows install, help, demo and mobile guidance

## Windows
- `scripts/start_medigen.bat` - starts the app on this PC and opens the browser. Waits on error so you can read it.
- `installer/MediGen.iss` - Inno Setup 6 script. Copies the project (never `.env`, `backups`, or uploaded profile pictures), creates `.env` from `.env.example` on first install only, runs `pip install -r requirements.txt`, adds Start-menu and optional desktop shortcuts, and stops with a message if Python is missing.
- `installer/README.md` - how to build `dist/MediGen_Setup_1.0.exe`, and what is NOT included (code signing, MySQL, auto-update).
- **Not compiled here.** Build it once on a Windows PC and test on a clean machine.

## Help and training
- `docs/HELP_CENTER.md` - 15 sections for pharmacy staff: start-up, roles, medicines, batches, sales, returns, purchases, prescriptions, alerts, reports, backups, users, settings, phone and API, troubleshooting.
- `docs/VIDEO_SCRIPTS.md` - six video scripts (install, stock, batches, sales, prescriptions, reports and backups), with a recording checklist. Demo data only.

## Demo data
- Already in the project: `database/sample_data.sql` (fictional names and numbers, run after `schema.sql`). It was not changed.

## Mobile app
- `docs/MOBILE_APP_GUIDE.md` - the PWA route (already working, needs HTTPS to install), and the APK options (LAN server, or hosted server with Trusted Web Activity / Capacitor). No APK was built.
- **Decision needed:** LAN only, or hosted on the internet.

## Tests
- `tests/test_sprint5_release.py` - 27 static checks on the files above. All pass.
- `python tests/run_all.py` - see the total in the zip caption.
