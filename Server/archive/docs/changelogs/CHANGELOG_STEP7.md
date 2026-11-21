# MediGen AI Pro - Step 7 (fast billing and offline files), part 1

## What changed
- **Barcode on medicines.**
  - New barcode field in the Add Medicine and Edit Medicine windows (optional).
  - Letters, digits and dashes only, 4 to 64 characters. Duplicates are refused.
  - Database column is added automatically on start (`medicines.barcode`).
- **Scanner box on the New Sale page.**
  - Type or scan a barcode, press Enter, and the medicine is added (quantity 1).
  - Scanning the same medicine again adds 1 more. Stock is checked each time.
  - Unknown barcode shows a message. The sale form is not submitted by the scanner's Enter key.
  - USB barcode scanners work without a driver: they type the code and press Enter.
- **Offline files script** `scripts/fetch_assets.py`.
  - Downloads Bootstrap, Bootstrap Icons and Chart.js into `static/vendor/` (versions pinned).
  - Run once on a computer with internet. See the note below.

## Important note: offline files
- The network used while building this step blocks the CDN, so the script could not be run here.
  It is written and compiles, but please run it on your own computer once and tell me the result.
- The pages still load these files from the internet until the switch is made (next part of Step 7).

## Tests
- Full mock suite: 443 pass, 2 fail (the 2 old profile tests, unchanged).
- `tests/test_barcode_step7.py` (new, 20 checks): barcode rules, duplicate check on add and edit, saved column, scanner box present, Enter handled, edit window gets the barcode.
- Mock tests for sales and prescriptions updated for the new column in the medicine query (test data only).

## Pharmacy benefit
- Counter billing: scan the box, get the medicine, press Enter. No searching through a long list.
- Fewer wrong medicines and fewer mistakes with similar names (Panadol 500 vs Panadol Extra).

## Part 2a (done): shared styles in one file
- The main style block (about 590 lines) moved from `templates/base.html` to `static/css/style.css`.
- `base.html` now links that file. Pages look the same; they are easier to change and to cache.
- `tests/test_frontend.py` now checks the CSS file for the phone menu rule.

## Not done yet (Step 7 part 2)
- Switch the pages to the local `static/vendor/` files, after the script has been run.
- Move the inline CSS to `static/css/style.css`, and the English / Roman Urdu labels (Step 6).
- Dark mode and the Plus Jakarta Sans font (also from the internet at the moment).

## Files to put in the project
- Replace: `static/css/style.css` (new folder `static/css/`), `templates/base.html`, `tests/test_frontend.py`, `pharmacy/core.py`, `pharmacy/lib.py`, `pharmacy/repos/medicines.py`, `pharmacy/routes/medicines.py`, `pharmacy/routes/sales.py`, `templates/medicines.html`, `templates/new_sale.html`, `tests/test_repos.py`, `tests/test_sales.py`, `tests/test_prescriptions.py`.
- New: `scripts/fetch_assets.py`, `tests/test_barcode_step7.py`, `CHANGELOG_STEP7.md`.
- Everything else stays the same.
