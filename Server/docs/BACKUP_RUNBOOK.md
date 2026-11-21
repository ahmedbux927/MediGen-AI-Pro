# MediGen AI Pro: Backup and Restore Runbook

The app does not make backups by itself. Backups are made with MySQL's `mysqldump`, using the script in `scripts/backup_db.py`.

## 1. Requirements
- `mysqldump` must be installed with MySQL 8 (it is in the MySQL `bin` folder, for example `C:\Program Files\MySQL\MySQL Server 8.0\bin`).
- If `mysqldump` is not on the PATH, set `MYSQLDUMP=C:\full\path\mysqldump.exe` in `.env`.
- `.env` must hold `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

## 2. Test once by hand
Open the project folder and run:

    python scripts/backup_db.py

You should see `Backup saved: ...backups\medigen_YYYYMMDD_HHMM.sql`. A failed run prints `BACKUP FAILED:` with the reason.

## 3. Schedule it every day

### Windows (Task Scheduler)
1. Open **Task Scheduler** > **Create Basic Task**.
2. Name: `MediGen daily backup`. Trigger: **Daily**, at 02:30.
3. Action: **Start a program**. Program: `scripts\backup_db.bat` with the full path to the project folder.
4. Finish. Right-click the task > **Run** to test it.

### Linux / macOS (cron)
Run `crontab -e` and add:

    30 2 * * * /path/to/medigen/scripts/backup_db.sh >> /path/to/medigen/backups/backup.log 2>&1

## 4. How many copies are kept
The script keeps the newest `BACKUP_KEEP` files (default 30) in the `backups` folder, and deletes older ones.

## 5. Keep a copy outside the PC
A backup on the same disk is lost if the disk fails. Copy the newest file once a week to a USB drive or a cloud folder (Google Drive, OneDrive).

## 6. Restore
Restoring replaces the data in the database. Test on a copy first.

1. Stop the app (`Ctrl+C` in the terminal, or close the desktop window).
2. Create an empty database, or drop the old one:

        mysql -u root -p -e "DROP DATABASE IF EXISTS pharmacy_management_system; CREATE DATABASE pharmacy_management_system CHARACTER SET utf8mb4;"

3. Load the backup:

        mysql -u root -p pharmacy_management_system < backups\medigen_20261017_0230.sql

4. Start the app and check the Dashboard, Medicines and Sales.

## 7. Checklist for every month
- [ ] A new backup file is in the `backups` folder.
- [ ] One restore test was done on a copy.
- [ ] A copy is stored outside the PC.
