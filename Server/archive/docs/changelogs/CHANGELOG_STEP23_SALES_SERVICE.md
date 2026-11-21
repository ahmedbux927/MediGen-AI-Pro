# Step 23 - Sales rules moved to a service (backend track, B3, v49.3)

## Added
- `pharmacy/services/sales.py`: the new-sale rules, without Flask:
  `read_lines` (form lines), `reserve_lines` (lock, stock check, FIFO batches), `calculate_bill`
  (discount, cashier limit, tax, paid, udhaar), `claim_guard` (double-submit), `save_sale` (sale, items,
  payment, audit row). Problems the cashier can fix raise `BillError` with the same messages as before.
- `tests/test_services_sales.py`: 26 checks, pure Python.

## Changed
- `pharmacy/routes/sales.py` `new_sale`: reads the form, calls the service, then flashes and redirects.
  Same URLs, same messages, same database writes.

## Not changed
- Templates and static files (freeze test passes). Routes, form fields and JSON are unchanged.

## Tests
- Result: 1165 passed (route tests) + 26 (service tests), 0 failed (mock database).

## Not tested here
- Real MySQL: run `python tests\run_all.py --live` on the shop PC, then make a test sale on the check database.
