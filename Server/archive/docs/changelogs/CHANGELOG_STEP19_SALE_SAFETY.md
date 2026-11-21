# Step 19 - Sale safety (backend)

## Changed
- `pharmacy/routes/sales.py` (new sale):
  - A medicine that was deleted after the page loaded is no longer dropped silently.
    The whole bill is rejected with: "A selected medicine no longer exists. Please reload the page and try again."
  - Medicine rows are locked in a fixed (id) order, so two sales that contain the same medicines cannot deadlock.
  - Non-numeric medicine ids are rejected ("Invalid medicine selected").
  - A bill is limited to 100 different medicines.

## Tests
- `tests/test_coverage_sales_lib.py`: unknown-medicine message updated; new checks for partial-missing bill,
  non-numeric id, and fixed lock order.
- Result: 1076 passed, 0 failed (mock database). Run `python tests\run_all.py --live` on the shop PC with MySQL.
