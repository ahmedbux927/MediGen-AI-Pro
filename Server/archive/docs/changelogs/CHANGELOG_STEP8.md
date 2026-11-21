# MediGen AI Pro - Step 8 (shared JavaScript and counter shortcuts)

## Fix in this package (important)
- `templates/base.html` in the Step 7 zip was cut to 228 lines. The design styles (about 590 lines) were missing,
  so pages looked plain. This package has the complete file (817 lines). Replace it.
- New guard test checks that base.html is complete, so this cannot happen silently again.

## What changed
- `static/js/app.js` (new): one shared file, loaded on every page, no internet needed.
  - `MediGen.post(url, body)`: sends POST requests with the security token (for future AJAX actions).
  - `MediGen.toast(message, type)`: small message at the top right. Uses textContent, so no HTML injection.
  - `MediGen.shortcut(key, fn)`: keyboard shortcut helper.
- Sale page (New Sale) keyboard keys:
  - **F2**: go to the barcode box (scan or type).
  - **F3**: add another item row and go to it.
  - **F4**: go to the Paid amount box.
  - **Esc**: clear the scan message.
  - A line under the scan box shows the keys.
- Shortcuts are set up after the page is ready, because app.js loads at the end of the page.
- No key completes the sale by itself. The staff member still presses the Complete Sale button, so a
  stray key cannot create a bill.

## Tests
- Full mock suite: 455 pass, 2 fail (the 2 old profile tests, unchanged).
- `tests/test_step8.py` (new, 12 checks): base template complete, app.js loads, token sent, no HTML injection,
  JavaScript syntax check (node), sale shortcuts present and delayed until ready, file served by the app.
- URL map: 66 routes (no change).

## Pharmacy benefit
- Counter staff can work with the keyboard only: scan, add item, enter paid amount. Faster line at the counter.

## Files to put in the project
- Replace: `templates/base.html` (important), `templates/new_sale.html`.
- New: `static/js/app.js`, `tests/test_step8.py`, `CHANGELOG_STEP8.md`.
- Also replace all files from the Step 7 zip (the `pharmacy/` folder, `templates/medicines.html`, tests) if not done yet.
- Everything else stays the same.

## Not done yet
- Switch pages to the local `static/vendor/` files (run `scripts/fetch_assets.py` first).
- Move inline CSS into `static/css/style.css`; English / Roman Urdu labels (Step 6); dark mode.
