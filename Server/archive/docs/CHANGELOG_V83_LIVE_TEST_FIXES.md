# MediGen v83 - Live test fixes and stock triggers checked at startup

## What the live test showed (your run of `run_all.py --live`)
1. **Sale did not lower stock (500 → 500)**, and the audit and prescription checks failed.
   - Test side: the test read stock once before the sale and read it again in the same transaction, so MySQL kept showing the old snapshot. Fixed: the test commits after the sale before reading again.
   - App side (real risk): a sale lowers stock only through the database trigger `trg_sale_stock`. That trigger was in `schema.sql` but the app did not create it at startup. If your database was made from an older schema, or its triggers were not in a restore, sales were saved and stock never moved, with no error. Fixed: startup now checks the sale and purchase triggers and creates a missing one.
2. **Stock count crashed**: "229 medicine(s) are not counted yet". The test counted only one medicine, but a count must cover every medicine before it is submitted (by design). Fixed: the test records every medicine.

## What changed
- `pharmacy/services/stock_triggers.py` (new): the two trigger definitions and the "what is missing" rule.
  - A table counts as covered if ANY insert trigger exists on it, under any name. So a trigger is never added twice (that would take the stock twice).
- `pharmacy/core.py`: `ensure_stock_triggers()` runs at startup, after the audit triggers. A missing trigger is created and logged as a WARNING. If it cannot be created (no TRIGGER permission), an ERROR is logged.
- `tests/test_live_mysql.py`: checks the sale trigger exists in the live database; commits before reading the new stock.
- `tests/test_live_backend.py`: stock count covers every medicine.
- `tests/test_stock_triggers.py` (new, 11 checks).

## Tests
- `tests/run_all.py` (without `--live`): 1526 passed, 0 failed.
- Please run `python tests\run_all.py --live` again on the shop PC.

## Check on the shop PC
1. Copy this project folder (v83) over the old one and restart. Your run used `MediGen_FULL_Project_v69`, so the newest fixes were not in that copy.
2. Look at the log (`logs\medigen.log`) after the first start:
   - `stock trigger ... was missing ... has been created` → your database had no sale or purchase trigger. Stock was not moving on sales until now. Please tell me; it may also mean past stock numbers need a stock count.
   - `stock triggers missing and could not be created` → the database user needs TRIGGER permission (grant it in MySQL, then restart).
   - No line → triggers were already there.
3. Run `python tests\run_all.py --live`. Expect the sale and count checks to pass.
