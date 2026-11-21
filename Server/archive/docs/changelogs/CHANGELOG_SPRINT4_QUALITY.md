# Sprint 4 - Dashboard accessibility and test coverage (complete)

## Dashboard charts (responsive + accessible)
- Both charts sit in a fixed-height box (260px, 220px on phones) and resize with the window.
- Each chart is `role="img"` with a title and a text description.
- Each chart has a screen-reader data table (Day / Invoices / Revenue, and Medicine / Units sold).
- Empty states: "No sales in the last 7 days yet." and "No sales recorded yet." instead of a blank chart.
- Contrast: doughnut slices `#a85f0a` and `#5b6b84`; stat-card labels `#5b6b84`.
- Reduced-motion preference respected.
- `/dashboard` passes `sales_rows` and `med_rows` to the template.
- `pages.css` is now `?v=35`.

## Bug fixed
- **Forgot password crashed** for any real username: `forgot_password` (routes/auth.py) called `_reset_hash`, which was defined only in routes/users.py. It is now defined in `pharmacy/core.py` and imported by both routes. Found by the new tests.

## Coverage tool (no extra packages)
- `python tests/measure_coverage.py` runs every mock test and reports line coverage for `pharmacy/`, `pharmacy/routes/` and `app.py`.
- `python tests/measure_coverage.py --min 80` exits with code 1 when total coverage is below 80%.
- It measures lines, not branches. It is an estimate.

## Coverage result
- Start of sprint: 53.5%. End: **81.4%** (2448 of 3006 lines).

## New test files
- `tests/test_sprint4_quality.py` - 9 checks for chart markup and CSS.
- `tests/test_coverage_sales_lib.py` - sales validation, discounts, payments, returns, prescriptions in sales, reports and settings helpers.
- `tests/test_coverage_admin.py` - users, login and forgot password, profile, password change, picture upload, settings, records clear, supplier-return validation.
- `tests/test_coverage_batches.py` - batch list and filters, write-off, reconcile.
- `tests/test_coverage_prescriptions.py` - list, add, edit, delete, receipt, allergy warnings.
- `tests/test_coverage_catalog.py` - categories, customers, suppliers.
- `tests/test_coverage_medicines.py` - list, add, edit, stock in/out, history, delete, export.

## Tests
- `python tests/run_all.py` - 859 passed, 0 failed.

## Install / update
1. Stop the server.
2. Replace the whole `MediGen` folder (keep `.env`, `backups/` and `static/profiles/`).
3. Run `python app.py`, then Ctrl+F5.
4. Check: `python tests/run_all.py` and `python tests/measure_coverage.py --min 80`.
