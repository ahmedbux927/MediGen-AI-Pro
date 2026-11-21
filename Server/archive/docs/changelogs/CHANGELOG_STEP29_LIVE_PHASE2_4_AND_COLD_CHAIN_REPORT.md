# Step 29 (v49.9): live checks for Phase 2-4 SQL, cold-chain lines in the daily report

Backend only. No template or static file changed.

## What changed
1. `tests/test_live_backend.py` (run with `--live` on a real MySQL server, database `medigen_live_test` only):
   - Held bill: hold, listed as open, resume returns the held lines, second resume refused.
   - Phone search: a customer saved as `0300-7654321` is found by `7654321`; too-short search returns nothing.
   - Stock count: start, count one medicine at +5, submit, approve as Admin; stock equals counted value; a `stock_adjustments` row with reason `Stock count` exists.
   - Controlled register: a scheduled medicine without prescription is refused; a register row written; UPDATE is rejected by the trigger.
   - Temperature: 9.5 C is saved with in_range = 0.
2. `scripts/inventory_report.py`: `summary.txt` gets a cold-chain line: count of readings out of range in the last 24 hours, with each location and time. If migration 006 is not applied, the line says the log is not available yet. The report stays read-only.

## Tests
- `python tests/run_all.py`: 1276 passed, 0 failed (mock DB). The live file is skipped without `--live`.
- Live run: NOT executed (no MySQL in the build environment). The first real run may show small SQL fixes; send the output.

## Known assumptions the live run will confirm
- `customers` columns: name, contact_number.
- `stock_adjustments` columns as used by `approve_count`.
- Trigger on `controlled_register` (created by `ensure_register_triggers` in `ensure_schema`).
