# MediGen AI Pro - Step 11O: Audit Log and Backup Removed

## Removed from the project
- Audit Log page (`/audit`, export and timeline), its templates, and its route file.
- Backup page (`/backup`, create, download, restore, delete), its templates, and its route file.
- Root `backup.py` module (dump, restore and auto-backup helpers).
- Daily automatic backup at start-up in `app.py` and `desktop.py`.
- Sidebar links for Backup and Audit Log.
- Audit Log link on the Reports page.
- Backup and audit statistics on Settings (backups count, audit protected tile).
- Audit and backup wording in profile, settings, and the 500 error page.
- Audit and backup styles in `pages.css` (only the customers table fix remains).
- Obsolete tests, and the backup/restore part of the live MySQL test.

## Kept on purpose
- The `audit_log` table, its append-only database triggers, and the internal `audit()` calls in sales, medicines, users and other routes. These run inside business transactions. Removing them touches almost every route. If you want those removed too, tell me and I will do it as a separate step.

## Verified
- `/backup` and `/audit` return 404.
- Sidebar, Reports and Settings have no audit or backup links.
- Tests: 499 passed, 0 failed (mock suite). The live MySQL test was updated but not run in this sandbox.

## Install
1. Replace the whole project folder. Delete the old `backup.py` and `templates/backup.html`, `audit_log.html`, `audit_timeline.html` if they remain.
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 499 passed).
