# MediGen AI Pro - Step 4 (login and user security)

## What changed
- **Login lock now in the database** (`login_attempts` table, created automatically on start).
  - Before: the lock was in memory, so a restart or a second worker reset it.
  - Now: 5 wrong passwords lock the username + IP for 5 minutes, even after a restart.
  - The table stores a SHA-256 hash of IP + username, not the raw values.
  - A successful login clears the counter. An expired lock is ignored and reset.
- **Same timing for unknown usernames.** Before, a wrong username answered faster than a wrong password, so an attacker could guess which usernames exist. Now the server always runs one bcrypt check.
- **Locked login is audited** (`login.locked`).
- **Add user checks:**
  - Username: 3 to 40 letters, numbers, dot or underscore.
  - Full name: 2 to 80 characters.
  - Role must be a real role id (checked in the database).
- **Access time checks:** start and end must be HH:MM (24 hour), e.g. 20:00 to 06:00.

## Pharmacy benefit
- A staff member who forgets the password cannot unlock the account by restarting the computer.
- Someone trying random usernames cannot tell which staff names exist.
- Wrong role or time values are caught before they are saved.

## Tests
- Mock suite: 396 pass, 2 fail (the 2 old profile tests, unchanged).
- `tests/test_auth_step4.py` (new, 20 checks): lock key hashing, lock persists in the table, lock expiry, counter reset on success, timing check, user input checks, access time checks.
- `tests/test_security.py` updated: its mock now stores the lock like the database does, and the add-user test uses a valid name.
- Not run here: the live MySQL test (`--live`). Run it on your scratch database before going live.

## Files to put in the project
- Replace: `app.py`, `pharmacy/core.py`, `pharmacy/routes/auth.py`, `pharmacy/routes/users.py`, `tests/test_security.py`.
- New: `tests/test_auth_step4.py`.
- Everything else stays the same.

## Not done in Step 4 (moved to later steps)
- One place for the role matrix (Step 4b or Step 5). Roles are still written in each route.
- Logout by POST only (Step 10).
- Password change and profile checks (Step 10).
