# Step 21 - Double-submit guard for sales (backend track, B1, v49.1)

## Added
- `pharmacy/services/sale_guard.py`: fingerprint of each bill (user, customer, payment, prescription,
  items and quantities, discount, amount paid). Item order does not matter.
- `sale_guard` table (created at startup if missing): fingerprint is the primary key.
- Window: 10 seconds. The same bill sent again inside the window is refused with the message
  "This bill was just saved. Check the sales list before adding it again." Nothing is written.
- Old guard rows are removed before each check, so a real repeat sale later is allowed.

## Changed
- `pharmacy/routes/sales.py` `new_sale`: the guard row is written in the same transaction as the sale,
  just before the sale insert.

## Not changed
- Templates and static files (no form field added). Freeze test still passes.

## Tests
- `tests/test_sale_guard.py`: 15 checks (fingerprint rules, window, duplicate error codes).
- `tests/test_coverage_sales_lib.py`: double-submit route test (5 checks, plus normal sale stores a fingerprint).
- Result: 1152 passed, 0 failed (mock database).

## Not tested here
- Real MySQL duplicate error (1062) on the shop PC: run `python tests\run_all.py --live`.
- Window is 10 seconds. A deliberate second identical bill within 10 seconds (rare) will be refused: the cashier
  must wait or change the bill (for example, a different quantity).
