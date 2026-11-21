# Offline assets (patch on top of v21)

## Why
Bootstrap, Bootstrap Icons and Chart.js were loaded from the internet on every page. Without internet the page kept spinning.

## What changed
- `pharmacy/lib.py`: new template helper `vendor_asset(local, cdn)`. It uses `static/vendor/<local>` when that file exists, otherwise the pinned CDN link.
- Templates `base.html`, `dashboard.html`, `reports.html`, `404.html`, `500.html`, `invoice.html`, `prescription_receipt.html` now use the helper.
- `scripts/fetch_assets.py` (already in the project) downloads the files into `static/vendor/`.
- `tests/test_offline_assets.py`: checks that every local path used by the templates is downloaded by `fetch_assets.py`.

## How to use
1. On a PC **with internet**, from the project folder: `python scripts/fetch_assets.py` (run once).
2. Restart `python app.py` and press Ctrl+F5.
3. Works offline from then on. Fonts (Plus Jakarta Sans) fall back to the system font if offline.
