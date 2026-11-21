# MediGen v82 - Restore one backup file into a new check database

## Why
- The project already has a daily backup: `scripts\backup_db.bat` (mysqldump, keeps the newest files in `backups\`).
- It already had a restore for a Workbench backup **folder** (`scripts/restore_backup.py`), which loads into a NEW check database and never touches the live one.
- The missing piece: restoring the **single .sql file** that the daily backup makes. This version adds it. (An earlier draft of a separate tool was removed, because it duplicated the existing scripts.)

## What changed
- `scripts/restore_backup.py` accepts one `.sql` file as well as a folder:
  ```
  python scripts\restore_backup.py backups\medigen_20261025_1200.sql --db pharmacy_restore_check
  ```
  - The file is loaded whole (tables, data, views and triggers in the order mysqldump wrote them).
  - Row counts are taken from the tables that exist in the new database.
  - A folder still needs `--prefix`, as before.
- Safety unchanged: the live database name is refused, and a database name that already exists is refused.

## Files
- `scripts/restore_backup.py` (updated), `tests/test_restore_single_file.py` (new, 7 checks).
- `.gitignore` unchanged (`backups/` was already ignored).
- The `backups\` folder is not in the zip (it contains patient and sales data).

## Tests
- `tests/run_all.py`: 1515 passed, 0 failed.
- Not run against a live MySQL yet.

## Steps on the shop PC
1. Run `scripts\backup_db.bat`. Note the new file in `backups\`. Copy it to a safe place too.
2. Test the restore into a new database (the live database stays as it is):
   ```
   python scripts\restore_backup.py backups\medigen_....sql --db pharmacy_restore_check
   ```
3. Compare the printed counts with the old system (users, sales, medicines, customers).
4. Only when the numbers match: set `MYSQL_DB` / `DB_NAME` in `.env` to `pharmacy_restore_check` to use it, and start the app.
5. Keep the old database until the restored one has worked for a day.
