# Step 26 - Stock count with variance approval (Phase 3, backend, v49.6)

## Added
- `database/migrations/003_stock_counts.sql`: tables `stock_counts` and `stock_count_lines` (created once, idempotent).
- `pharmacy/services/stock_count.py`:
  - states: open -> submitted -> approved (Admin only); open -> cancelled; submitted -> open.
  - only one count can be open at a time; start saves every medicine's current stock.
  - counted quantities can be changed while open; submit needs every line counted.
  - approval is refused if stock changed during the count (for example a sale), and asks for a new count.
  - approval sets stock to the counted value, writes one `stock_adjustments` row (reason "Stock count") and one
    audit row per changed medicine. Batches are not changed: run the batch sync tool afterwards.
- `scripts/stock_count.py`: command line for start, show, count (by barcode or medicine id), submit, cancel, approve.
  Every command needs `--by USERNAME`.
- `tests/test_stock_count.py`: 24 checks (rules and database steps, mock cursor).

## Not included yet
- A screen for counting (needs the frontend track), and a scanner-driven count screen.
- Batch-level counts. Counts change medicine totals only.

## Not changed
- Templates and static files (freeze test passes).

## Tests
- Result: 1225 passed, 0 failed (mock database).
- Not run on real MySQL yet. First try on the check database: start, count two items, submit, cancel (no stock change).
