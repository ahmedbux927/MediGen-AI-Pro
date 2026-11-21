# Live test root cause, old test files, admin name (v38 -> v39)

## Root cause of the live test login failure
- `config.py` reads DB_NAME, DB_HOST, DB_USER and DB_PASSWORD once, when it is first imported.
- The live test set DB_NAME to `medigen_live_test` AFTER importing config.
- So the app connected to the real `pharmacy_management_system` database, where the test user does not exist.
- Result: login failed and every page redirected to login (302).
- Fix: the test sets its environment variables BEFORE importing config, and asserts that the database name is the test database.
- Earlier test-only fixes stay: real CSRF tokens on every POST, and no dependence on HTTPS_ONLY.

## Note for the real database
- The failed live-test logins may have written a `login.fail` line to the real audit log. The audit log is append-only by design, so that line stays. It is harmless.

## Old test files
- `scripts/remove_old_test_files.py` deletes exactly the 12 old test files that are not part of this version.
- Run it once, then copy the `tests` folder from this zip.

## Admin name
- `database/rename_admin.sql` changes the Admin account named `Ahmed` to `Admin: CEO`. Run it in the MySQL client with `source database/rename_admin.sql`.

## Results here
- Mock suite: 1044 passed, 0 failed.
- Live MySQL test: not run here (no MySQL in the sandbox). Run `python tests\run_all.py --live` on the shop PC.
