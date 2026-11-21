# Step 25 - Inventory automation: expiry buckets, low-stock severity, purchase suggestions (backend track, B7, v49.5)

## Added
- `pharmacy/services/inventory.py` (pure rules):
  - `expiry_buckets`: expired, 0-30, 31-60, 61-90 days (batches expiring after 90 days are left out).
  - `low_stock`: severity `out` (0 in stock), `critical` (below half the reorder level), `low` (at reorder level).
  - `purchase_suggestions`: order up to twice the reorder level, grouped by the supplier of the latest received
    purchase; medicines with no purchase history go under "No supplier history".
- `scripts/inventory_report.py`: daily report, read-only. Writes `expiry_buckets.csv`, `low_stock.csv`,
  `purchase_suggestions.csv` and `summary.txt` into `reports\YYYY-MM-DD\` (or `--out`).
- `tests/test_inventory.py`: 10 checks.

## Scheduling (Windows Task Scheduler, no code needed)
- Program: `python`; arguments: `scripts\inventory_report.py`; start in: the project folder; daily at 08:00.

## Not included yet
- Stock count sessions with variance approval (larger change, next step).
- Sending the report by WhatsApp or email.

## Not changed
- Templates and static files (freeze test passes). The existing Alerts page and its 90-day check still work as before.

## Tests
- Result: 1201 passed, 0 failed (mock database).
- The report script's database queries are not run by the tests. Run it once on the check database:
  `python scripts\inventory_report.py` and check the four files.
