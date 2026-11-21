# MediGen v64 - merged project (v54.1 backend + v63 frontend)

## Changes from v63
- Included the v54.1 live-test fixes (tests only):
  - tests/test_live_backend.py seeds roles (Admin, Pharmacist, Cashier) before users are inserted (fixes FK error 1452).
  - tests/test_live_mysql.py shows the flashed message when a sale is not saved.
- Kept from v63: E-302 code for user add, and file logging to logs/medigen.log.

## Test
- tests/run_all.py: 1341 passed, 0 failed (mock database).
- Live MySQL run (run_all.py --live) not done here; needs MySQL on the shop PC.

## Important
- The v54.1 notes say the shop PC folder is NOT this lineage (about 160 test suites, audit and backup pages, bento.css).
  Test this zip in a NEW, EMPTY folder. Copy .env, backups and static\vendor from the old folder into it.
