# Step 27 - Phase 2 backend: hold and resume bills, phone search (v49.7)

## Added
- `database/migrations/004_held_bills.sql`: `held_bills` table (counter number, user, customer, JSON payload,
  status open / resumed / discarded / expired).
- `pharmacy/services/held_bills.py`:
  - hold a bill at a counter (1 to 20); at most 10 open holds per counter;
  - list open holds; resume once (the bill comes back as data); discard;
  - `expire_old_holds` marks holds older than 24 hours as expired (run from the daily job).
  - Holding does NOT reserve stock. Completing the resumed bill runs the normal stock check.
- `pharmacy/services/phone_search.py`:
  - normalises 0300-1234567, +92 300 1234567, 00923001234567, 3001234567 to the same digits;
  - searches customers by phone, shows the last sale date and the balance owed; needs at least 4 digits; max 50 results.
- `tests/test_phase2_backend.py`: 22 checks.

## Not included yet
- Screens for hold, resume and phone search (frontend track). The services are ready for them.
- Receipt JSON for the thermal printer: the 80mm receipt template already exists.

## Not changed
- Templates and static files (freeze test passes). No route or URL changed.

## Tests
- Result: 1247 passed, 0 failed (mock database).
- Not run on real MySQL yet. The SQL for phone search uses REPLACE and LIKE; check it on the check database with a real number.
