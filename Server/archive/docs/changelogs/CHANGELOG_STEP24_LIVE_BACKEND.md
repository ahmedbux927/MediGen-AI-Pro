# Step 24 - Live backend tests on real MySQL (backend track, B4, v49.4)

## Added
- `tests/test_live_backend.py` (runs only with `run_all.py --live`): on a scratch database `medigen_live_test`,
  it checks:
  - schema_version records migration 002, and a second run applies nothing;
  - product columns and the unique barcode index exist;
  - product import: dry run has no errors, commit creates one medicine and one batch per new product,
    existing items keep their stock, and a second import creates nothing;
  - double submit on a real sale saves exactly one sale;
  - the audit log triggers exist.

## Changed
- `tests/run_all.py`: `--live` runs both live files (`test_live_mysql.py`, `test_live_backend.py`); without
  `--live` both are skipped.

## Not tested here
- The live test was written in a sandbox that has no MySQL server or MySQL client library, so it has NOT been
  run. Expect small SQL or fixture fixes on the first real run. Run:
  `python tests\run_all.py --live` on the shop PC (or a PC with MySQL 8) and send me the output.
