# MediGen v80 - One-click start file for Windows

## What changed
- New file **START_MEDIGEN.bat** in the project folder. Double-click it to start the app.
- It checks, in order:
  1. `.env` exists (if not, it tells you to copy `.env.example` and set the password).
  2. Python is installed.
  3. Packages from `requirements.txt` are installed (first run only takes a few minutes).
  4. Starts `python app.py` and keeps the window open.
- Nothing else changed. The code is the same as v79.

## Before the first start (one time)
1. Install **Python 3.11+** (tick "Add Python to PATH").
2. Start **MySQL** (MySQL Server service, or XAMPP / MySQL Workbench as you already use).
3. Copy `.env.example` to `.env`. Set `DB_PASSWORD` and `SECRET_KEY`. Do not share this file.
4. Double-click **START_MEDIGEN.bat**. Open the address the window shows (for example `http://127.0.0.1:5000`).

## Notes
- If `pip` fails because of `mysqlclient` or `flask-mysqldb`, send the red error text. That is the one package that often needs Microsoft C++ Build Tools on Windows.
- Closing the black window stops the app.

## Tests
- `tests/run_all.py`: 1508 passed (no code change).
