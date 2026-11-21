# Profile save fix and missing-column migration (v39 -> v40)

## Cause
- Databases made from an older schema were missing some columns in the `users` table (for example `position`, `honors`, `about`, `access_start_time`).
- The profile save writes those columns, so MySQL answered "Unknown column", and the app showed "Could not save your profile".
- `ensure_schema()` only added missing columns for `sales` and `audit_log`, not for `users`.

## Fix
- `ensure_schema()` now adds every missing `users` profile and access column automatically the first time the app starts. Each added column is logged.
- Future schema changes: add the column to the list in `ensure_schema()` (USER_COLUMNS), and the test `tests/test_user_columns_migration.py` checks it.

## Tests
- `tests/test_user_columns_migration.py` (3 tests): every profile field has an auto-add, access and picture columns are covered, the migration runs during schema setup.
- Full mock suite: 1047 passed, 0 failed.

## Settings page
- Checked the save code: uses `app_settings` (created automatically, primary key on setting_key). No change needed.

## Still to check on the shop PC
- Restart the server once (so the migration runs), then save My Profile again.
- Look at `logs\server.log` for "Added missing users.<column> column" lines.
