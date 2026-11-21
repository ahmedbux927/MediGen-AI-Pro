# MediGen v65 - Phase 1: Fast POS (New Sale page)

## Added
- Scan with quantity: type `3*barcode` (or scan after typing `3*`) to add 3 pieces in one scan. Stock is checked for the total.
- F9 completes the sale from anywhere on the page (same as the Complete Sale button; does nothing if no medicine is picked).
- Key hint line now shows F9 and the 3*barcode rule.

## Unchanged
- Backend: no change. The server still checks stock, batches, prescriptions, discount caps and double submit.
- F2 scan box, F3 add item, F4 paid amount, Esc clear message, camera scan.

## Tested
- Mock DB page in Playwright: 3*barcode adds 3; a second scan adds 2 more (total 5); 99*barcode shows "Only 10 in stock"; F9 posts the form.
- tests/run_all.py: 1341 passed, 0 failed.

## Not done yet in Phase 1
- Auto print receipt after F9 (check the receipt page on the shop PC first).
- Customer quick-pick by phone number.
- Test with a real USB barcode scanner on the shop PC.
