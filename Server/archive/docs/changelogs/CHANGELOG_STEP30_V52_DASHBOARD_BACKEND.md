# Step 30 (v52): backend for the v52 dashboard (read-only)

Backend only. No template or static file changed. Source: BACKEND_REQUEST_V52.md.

## What changed in pharmacy/routes/dashboard.py
1. `pending_po`: COUNT of purchase_orders with status 'Pending'.
2. `recent_sales`: last 5 sales (sale_id, sale_date, total, returned_amount, customer or 'Walk-in').
   - invoice = "INV-" + 6-digit sale id (display only; sales has no invoice column).
   - status = 'Returned' when returned_amount > 0, else 'Completed'.
   - date = 'dd Mon yyyy'; empty string when sale_date is NULL.
3. `top_med_revenue`: SUM(si.subtotal) added to the existing top-selling query (same rows and order as top_med_names). Gross value, not net of returns.

## Notes
- The three values are passed to render_template. The current dashboard.html does not use them yet, so nothing on screen changes until the v52 template reads them.
- Only SELECT statements were added. Test asserts no INSERT/UPDATE/DELETE on the dashboard request.

## Tests
- tests/test_dashboard_backend.py: 12 checks (mock DB).
- python tests/run_all.py: see TOTAL line in the console run for this version.
- Not run against real MySQL.
