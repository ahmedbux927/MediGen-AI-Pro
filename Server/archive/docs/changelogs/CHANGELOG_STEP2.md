# MediGen AI Pro - Step 2 (structure)

## What changed
- `app.py` is now a short start-up file (about 70 lines). It starts the app and keeps the start-up checks.
- All code moved into the `pharmacy/` package:
  - `pharmacy/core.py`: Flask app, database handle, CSRF, login lock, schema checks, login and role decorators.
  - `pharmacy/lib.py`: shared helpers (settings, audit log, prescription checks, reports, chat, backup helpers).
  - `pharmacy/routes/`: one file per area: auth, dashboard, medicines, batches, catalog (categories, customers, suppliers), sales, purchase, prescriptions, audit, reports, users, chatbot, profile, records, settings, backup, errors.
- No URL, page name or form field changed. All 64 routes match the previous version exactly.
- `desktop.py`, `build_exe.bat` and `MediGen_AI.bat` work without changes (they still start `app`).

## Tests
- Mock suite: 349 pass, 2 fail. The 2 failures were there before (profile tabs and profile-update audit).
- Two tests read `app.py` as text. They now read the `pharmacy/` files too. One test sets a module value that moved (`BACKUP_DIR`, `_schema_ready`) and now sets it where the code reads it.

## Files to put in the project
- Replace: `app.py`, `tests/test_audit_log.py`, `tests/test_settings_backup.py`.
- New folder: `pharmacy/` (copy the whole folder, keep the `routes` sub-folder).
- Keep as before: `config.py`, `backup.py`, `chatbot_engine.py`, `templates/`, `static/`, `database/`.

## Not changed yet
- Repository (data) layer: Step 3.
- Templates and CSS: Steps 6 and 7.
