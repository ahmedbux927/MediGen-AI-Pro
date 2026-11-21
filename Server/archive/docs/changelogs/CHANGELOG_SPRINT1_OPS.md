# MediGen AI Pro - Sprint 1: Backup, Alerts, Supplier Returns

## Added
- **Daily backup:** `scripts/backup_db.py` (mysqldump, keeps the newest 30 files), `scripts/backup_db.bat` (Windows Task Scheduler), `scripts/backup_db.sh` (cron). Runbook: `docs/BACKUP_RUNBOOK.md` (schedule, off-PC copy, restore steps).
- **Alerts page** (`/alerts`, Admin and Pharmacist): low stock, expiring in 90 days, expired batches that still have units. Sidebar link "Alerts".
- **Supplier Returns** (`/supplier-returns`, Admin and Pharmacist): record expired, damaged, recalled or other stock sent back to a supplier. The units are removed from the batch and the stock, a stock history line is written ("Supplier return"), and the return is kept in a new `supplier_returns` table. The batch is locked during the save; errors roll back. Sidebar link "Supplier Returns".

## Test
- `tests/test_sprint1_ops.py`: 20 checks (backup command, password not on command line, retention, failure handling, routes, roles, locking, navigation).
- Full suite: 501 passed, 0 failed.
- Not yet run: the live MySQL test on a real database (run `python tests/run_all.py --live` on your PC).

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5. The new table is created automatically on start.
3. Set up the daily backup as in `docs/BACKUP_RUNBOOK.md`.
