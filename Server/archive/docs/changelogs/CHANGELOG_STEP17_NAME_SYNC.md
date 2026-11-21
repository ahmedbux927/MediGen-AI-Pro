# Name and role follow the database (v40 -> v41)

## Problem
- A name changed in My Profile or on the Users page was saved in the database, but the sidebar, the dashboard and the "Welcome back" line kept the old name.
- The name was stored in the login session and only refreshed at the next login.

## Fix
- `_sync_session_user()` (before every request, in `pharmacy/core.py`) reads the user's name and role from the database and updates the session.
- If the account is deactivated, the user is logged out at once.
- If the database gives no answer, the session is kept (the page still opens).
- Known limit: a deleted account's session ends after the idle timeout (30 minutes).

## Test fakes updated
- `test_business_step5`, `test_step10_security`, `test_coverage_admin`: fake databases now return the role for the user id, like the real database. The cashier test uses user id 3.

## Tests
- `tests/test_session_sync.py` (4 tests).
- Full mock suite: 1047 passed, 0 failed.
