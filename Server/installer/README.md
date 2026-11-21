# Windows installer — how to build

**Easiest: double-click `MAKE_WINDOWS_APP.bat`** in the Server folder. It runs
both steps below and tells you if something is missing.

Manual steps:

1. Run `build_exe.bat` (Server folder). It installs the Python requirements
   plus PyInstaller and builds `dist\MediGenAIPro\MediGenAIPro.exe`, copying
   `templates`, `static`, `database` and `scripts` next to it, plus a `.env`
   (from yours, or from `.env.example` — set `DB_PASSWORD` in it).
2. Install **Inno Setup 6** (free) from https://jrsoftware.org/isinfo.php
3. Open `installer\MediGen.iss` and press **Compile** (or run
   `iscc installer\MediGen.iss`). The installer appears as
   `dist\MediGen_Setup_<version>.exe` — one file that installs on any
   Windows PC. The target PC does **not** need Python.

## What the installer does

- Installs per-user to `%LOCALAPPDATA%\MediGen AI Pro` (no admin rights
  needed, so the app can write its backups and database files).
- Start-menu and optional desktop shortcuts run `MediGenAIPro.exe`, which
  opens the program in its own window (the server runs inside it).
- `.env` is installed on first install only and is **never** overwritten by
  an update; `backups` and profile pictures are likewise kept.

## MySQL on the target PC — two ways

- **Installed MySQL 8** (the usual shop setup): nothing special; the app
  uses the `DB_*` settings in `.env`.
- **Portable MySQL carried inside the Setup:** download the "MySQL 8.0 ZIP
  Archive" from mysql.com, unzip it, rename the folder to `mysql` and put it
  in the Server folder **before** building. `build_exe.bat` copies it into
  the build and the app starts it automatically (data lives in
  `mysql-data` next to the program; first run creates it and sets random
  passwords — see `bundled_mysql.py`). The Setup file gets large
  (MySQL is a few hundred MB) but then the target PC needs nothing at all.

## Not included (needs your decision or a purchase)

- **Code signing.** Without a certificate, Windows SmartScreen shows
  "Unknown publisher" the first time; users click "More info → Run anyway".
  An OV/EV code-signing certificate removes the warning.
- **Auto-update.** Not included. A new Setup installs over the old one and
  keeps `.env`, `backups` and profile pictures.

## Testing the installer

Install on a clean Windows PC (or a VM) once before giving it to a pharmacy.
Check: the shortcut opens the program window, the login page loads, a sale
completes, Settings → Backup now works, and uninstall removes the program
but leaves `.env` and `backups` (delete them by hand if you want them gone).
