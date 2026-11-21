# MediGen v71 - Auto-print receipt after a POS sale (Phase 1 leftover)

## What changed
- After a sale is saved from the POS (button or F9), the app opens the 80 mm thermal receipt with `?print=1`, and the print dialog opens automatically.
- The manual "Print 80mm receipt" button still works.
- The A4 invoice is still available at `/invoice/<id>` (sales list, returns, etc.). Only the POS redirect changed.

## Files
- `pharmacy/routes/sales.py`: POS success redirect → `invoice_thermal(sale_id, print=1)`.
- `templates/receipt_thermal.html`: small script; if `print=1`, calls `window.print()` after load.
- `tests/test_autoprint_receipt.py` (4 source checks, new).

## Tests
- `tests/run_all.py`: 1351 passed, 0 failed.
- Freeze manifest regenerated.

## To revert to the A4 invoice after sale
Change the redirect in `pharmacy/routes/sales.py` back to `url_for('invoice', sale_id=sale_id)` and update the test in `tests/test_autoprint_receipt.py`.

## Check on the shop PC
1. Copy v71 over the project (keep `.env` and `logs`), restart the server, Ctrl+F5.
2. Make a sale with F9. The receipt should open and the print dialog should appear.
3. Check the printer (thermal printer driver must be set as default or chosen in the dialog).
