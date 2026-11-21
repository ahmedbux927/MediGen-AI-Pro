# MediGen AI Pro - Changelog

Major versions only. Full older notes are in archive/docs/changelogs/ (not needed for daily use).

## Current: v101.03
- NEW ICON (owner asked, made with Canva): navy rounded square, white cross, teal pulse and leaf — now the Windows exe icon, installer icon, login/sidebar logo, favicon, PWA icons and the Android launcher icon, all derived from one verified master.
- USER DELETE FIXED (owner: "ak user delete nhi ho raha tha"): references are now scanned completely — user_id columns plus every foreign key by name (counted_by, created_by, ...) — and the delete dialog offers "Delete permanently": the account is removed and its sales/records move to a 'Deleted user' placeholder, so shop history stays complete. The last active Admin and the placeholder itself are protected.
- Full check: every route behind the global error handlers, no bare or silent exceptions anywhere, all files compile, dark-mode inline-style audit (product-edit Back button now follows the theme), font sizes verified. Suite 2509 passed, 0 failed.

## v101.02
- Windows app build completed and fixed: MAKE_WINDOWS_APP.bat builds the exe and then the single Setup file in one run. Found and fixed a real defect — inside the built exe, Settings → Backup now / Restore test could not run their scripts (no loose Python in a PyInstaller build); the exe now runs them via its own --script mode, and build_exe.bat ships the scripts folder next to the exe. The installer README was rewritten to match what the installer actually does, including the portable-MySQL option.

## v101.01
- Theme now follows the computer: System mode (default) uses the Windows light/dark setting and updates live when it changes; the top-bar button cycles System → Light → Dark. The login page follows the same choice. Older saved choices are respected.
- Installer script version aligned (MediGen_Setup shows 101.01).

## v101.00 (Master Prompt v4 — Stages 0-12)
- Typed error system wired end to end: clean English messages for users, detail only in logs; no silent failures.
- Held Bills page (hold a bill, resume it later); pack selling (`2pk*barcode`) with Units per pack on the product page.
- Import with preview: upload → check every row → Confirm → Undo (blocked once an imported item is sold or bought).
- AI Pro guardrails: 20 questions/minute per user, 10-minute answer cache (live figures never cached), optional Daily AI Summary on the dashboard (off by default; only totals are sent to Gemini).
- One design bundle: the app now loads a single generated app.css; double-submit guard on forms; Medicines page fully dark in dark mode.
- Settings: Reset to defaults per group; Users: edit name and role (the last Admin cannot be demoted).
- Android: LAN-only server address validation with unit test, camera permission for barcode scanning, Gradle project (AGP 8.5.2).
- Barcode label printing (Code 128 PDF) on the Medicines page.
- Full QA recorded in QA_MATRIX.md: 38 routes x 4 roles, CSRF proven, migrations double-run clean, 1000-medicine timings.

## v100.00
- Gemini is the only AI provider (OpenAI and Claude removed).
- Old phone-only code, license feature and extra modules moved to archive/.
- Android app kept in android/ (WebView app for the shop PC server over LAN).

## From CHANGELOG_CHARTS.md

# Charts fix (patch v23)

## Problem
- Dashboard "Last 7 days" bar chart skipped days with no sales, so the bars did not line up with the calendar.
- The query used `INTERVAL 7 DAY`, which covered 8 days, not 7.
- Reports "Daily Revenue Trend" / "Daily Sales" chart also skipped days (the docs said it was filled; the code was not).
- Dashboard "Top sellers" counted sold units before returns, while Reports counted them after returns, so the two pages could disagree.
- Browser Back could show a dashboard or report page from before the latest sale.

## Fix
- `pharmacy/lib.py`: new `_fill_days(rows, start, end, key)` gives one point per calendar day, zero where there were no sales.
- `pharmacy/routes/dashboard.py`: exact 7-day window (today and the 6 days before). Top 5 sellers are now net of returns and only include medicines with units left after returns. Empty-state flag `chart_has_data`. Response sends `Cache-Control: no-store`.
- `pharmacy/routes/reports.py`: the daily chart uses `_fill_days` for the selected range. Response sends `no-store`.
- `templates/dashboard.html`: the sales chart shows "No sales in the last 7 days yet." only when all 7 days are zero.
- `tests/test_charts_data.py`: 12 new checks.

## Files
- pharmacy/lib.py
- pharmacy/routes/dashboard.py
- pharmacy/routes/reports.py
- templates/dashboard.html
- tests/test_charts_data.py
- CHANGELOG_CHARTS.md

## Test result
- Full mock suite: 941 passed, 0 failed.

## Notes
- Charts are drawn from the database on every page load. Refresh or open the page again after a sale to see it.
- A very long reports range (for example several years) gives one point per day, so the line becomes dense. The presets (7 days, 30 days, 1 year) are fine.

## From CHANGELOG_OFFLINE_ASSETS.md

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

## From CHANGELOG_SPRINT1_OPS.md

# MediGen AI Pro - Sprint 1: Backup, Alerts, Supplier Returns

## Added
- **Daily backup:** `scripts/backup_db.py` (mysqldump, keeps the newest 30 files), `scripts/backup_db.bat` (Windows Task Scheduler), `scripts/backup_db.sh` (cron). Runbook: `docs/BACKUP_RUNBOOK.md` (schedule, off-PC copy, restore steps).
- **Alerts page** (`/alerts`, Admin and Pharmacist): low stock, expiring in 90 days, expired batches that still have units. Sidebar link "Alerts".
- **Supplier Returns** (`/supplier-returns`, Admin and Pharmacist): record expired, damaged, recalled or other stock sent back to a supplier. The units are removed from the batch and the stock, a stock history line is written ("Supplier return"), and the return is kept in a new `supplier_returns` table. The batch is locked during the save; errors roll back. Sidebar link "Supplier Returns".

## Test
- `tests/test_sprint1_ops.py`: 20 checks (backup command, password not on command line, retention, failure handling, routes, roles, locking, navigation).
- Full suite: 501 passed, 0 failed.
- Not yet run: the live MySQL test on a real database (run `python tests/run_all.py --live` on your PC).

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5. The new table is created automatically on start.
3. Set up the daily backup as in `docs/BACKUP_RUNBOOK.md`.

## From CHANGELOG_SPRINT2_REPORTS.md

# MediGen AI Pro - Sprint 2: Excel, PDF and Sales Tax Summary

## Added
- Reports export to **Excel (.xlsx)** and **PDF** as well as CSV. The Sales tab has Excel and PDF buttons.
- **Sales tax summary** (Admin): one line per day with subtotal, discount, tax, total and returns, plus totals at the bottom. Available as Excel and PDF from the Sales tab.
- The tax summary says plainly that tax on returned sales is not reversed automatically, and that the rate and filing rules must be confirmed by the tax advisor.
- New file `pharmacy/exports.py` builds the Excel and PDF files (no database code, easy to test).
- `requirements.txt`: added `openpyxl` and `reportlab`.

## Test
- `tests/test_sprint2_exports.py`: 19 checks (file formats, numbers kept as numbers, summary and notes, empty reports, wiring).
- Full suite: 520 passed, 0 failed.

## Install
1. Replace the project folder.
2. `pip install -r requirements.txt` (adds openpyxl and reportlab).
3. `python app.py`, then Ctrl+F5.

## From CHANGELOG_SPRINT3_API_PWA.md

# Sprint 3 - REST API (read-only), API tokens, Installable PWA

## What's new

### 1. API tokens
- New table `api_tokens` (created automatically by `ensure_schema`).
- Tokens look like `mgk_...`. The raw token is shown ONCE when created. Only a SHA-256 hash is stored.
- Roles allowed for tokens: **Admin** or **Pharmacist** only.
- Create a token:

  ```
  python scripts/create_api_token.py "Label" Admin
  python scripts/create_api_token.py "Label" Pharmacist
  ```

### 2. Read-only REST API (`/api/v1/`)
Send the token as a header: `Authorization: Bearer mgk_...`

| Endpoint | Who | What |
|---|---|---|
| `GET /api/v1/health` | no token | Server status check |
| `GET /api/v1/medicines?q=&page=&per=` | Admin, Pharmacist | Medicine list (`per` max 100). `cost_price` is returned to **Admin only** |
| `GET /api/v1/stock/low` | Admin, Pharmacist | Low-stock medicines |
| `GET /api/v1/batches/expiring?days=` | Admin, Pharmacist | Batches expiring within `days` (1-365) |
| `GET /api/v1/sales/summary?from=&to=` | Admin | Sales totals for the period |

- Success responses: `{"data": [...], "meta": {"page", "per", "total"}}`.
- There are **no write routes**. The API cannot create, change or delete data.
- Revoked tokens (`revoked = 1`) are refused. `last_used` is updated on each call.

### 3. Installable app (PWA)
- `/manifest.webmanifest` - app name, icons, standalone display, theme `#0f9aa0`.
- `/sw.js` - service worker. It caches **only** GET requests for `/static/` files (cache `medigen-static-v1`). Pages and API responses are never cached.
- Icons: `static/icons/icon-192.png`, `icon-512.png`.
- `base.html` links the manifest and registers the service worker.

**Important:** browsers install the app and register the service worker only on
- `https://...` addresses, or
- `http://localhost` / `127.0.0.1`.

On a plain LAN address such as `http://192.168.x.x:5000`, the app works normally but cannot be installed and the service worker does not register. Use HTTPS (reverse proxy or hosting) for phone installs.

## Files
- New: `pharmacy/api_auth.py`, `pharmacy/routes/api.py`, `pharmacy/routes/pwa.py`, `scripts/create_api_token.py`, `static/js/sw.js`, `static/manifest.webmanifest`, `static/icons/icon-192.png`, `static/icons/icon-512.png`, `tests/test_sprint3_api.py`, this changelog.
- Changed: `pharmacy/core.py` (api_tokens table), `pharmacy/routes/__init__.py` (registers api and pwa), `templates/base.html` (manifest, theme colour, service worker).

## Tests
- `python tests/test_sprint3_api.py` - 26 checks, all pass.
- `python tests/run_all.py` - 546 passed, 0 failed.

## Install / update
1. Stop the server.
2. Replace the whole `MediGen` folder with the new one (keep your `.env` and `backups/`).
3. Run `python app.py` and press Ctrl+F5 in the browser.
4. Optional: `python scripts/create_api_token.py "My app" Admin` to create a token.

## From CHANGELOG_SPRINT4_QUALITY.md

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

## From CHANGELOG_SPRINT5_RELEASE.md

# Sprint 5 - Windows install, help, demo and mobile guidance

## Windows
- `scripts/start_medigen.bat` - starts the app on this PC and opens the browser. Waits on error so you can read it.
- `installer/MediGen.iss` - Inno Setup 6 script. Copies the project (never `.env`, `backups`, or uploaded profile pictures), creates `.env` from `.env.example` on first install only, runs `pip install -r requirements.txt`, adds Start-menu and optional desktop shortcuts, and stops with a message if Python is missing.
- `installer/README.md` - how to build `dist/MediGen_Setup_1.0.exe`, and what is NOT included (code signing, MySQL, auto-update).
- **Not compiled here.** Build it once on a Windows PC and test on a clean machine.

## Help and training
- `docs/HELP_CENTER.md` - 15 sections for pharmacy staff: start-up, roles, medicines, batches, sales, returns, purchases, prescriptions, alerts, reports, backups, users, settings, phone and API, troubleshooting.
- `docs/VIDEO_SCRIPTS.md` - six video scripts (install, stock, batches, sales, prescriptions, reports and backups), with a recording checklist. Demo data only.

## Demo data
- Already in the project: `database/sample_data.sql` (fictional names and numbers, run after `schema.sql`). It was not changed.

## Mobile app
- `docs/MOBILE_APP_GUIDE.md` - the PWA route (already working, needs HTTPS to install), and the APK options (LAN server, or hosted server with Trusted Web Activity / Capacitor). No APK was built.
- **Decision needed:** LAN only, or hosted on the internet.

## Tests
- `tests/test_sprint5_release.py` - 27 static checks on the files above. All pass.
- `python tests/run_all.py` - see the total in the zip caption.

## From CHANGELOG_STEP1.md

# MediGen AI Pro - Step 1 (cleanup)

## Removed
- Manufacturer feature: routes, pages, menu link, medicine form field, search, CSV column, chatbot entity.
- Database: `manufacturers` table and `medicines.manufacturer_id` (dropped automatically on first start).

## Changed (security and permissions)
- `config.py`: no fixed fallback SECRET_KEY. A random key is used when `.env` has none (logins reset on restart).
- Cashier can no longer receive payments (`/sales/<id>/pay`), per the role matrix.
- Customer delete is limited to Admin and Pharmacist.
- NaN and infinity are rejected in sale discounts, payments, medicine prices and purchase prices.
- Audit log now records: records clear, user add, delete, active toggle, access-time change.

## Breaking changes
- Medicine add/edit no longer asks for a manufacturer.
- Medicine CSV export has no Manufacturer column.
- Old manufacturer data is deleted by the migration. Make a backup before the first start.

## Tests
- New: tests/test_step1_cleanup.py (19 checks).
- Mock suite: all results the same as before Step 1, except the new suite. Two failures were already there before this step (profile tabs and profile-update audit).

## Not changed yet (waiting for decision)
- Dispensed prescriptions can still be edited. The tests expect this, the manual checklist says it must be locked.
- "In" stock adjustments do not update batches (needs an expiry decision).
- Raw database error text shown in flash messages (Step 10).

## From CHANGELOG_STEP10.md

# MediGen AI Pro - Step 10 (Security and Cashier privacy), part 1

## What changed
- **Safe error messages.** Pages no longer show technical errors such as database text.
  - The user sees a short message, for example "Backup failed. Please try again."
  - The full error goes only to the server log (terminal).
  - 37 places in 14 route files now use the one helper `flash_unexpected()` in `pharmacy/lib.py`.
  - Validation messages (wrong input) still show their own clear text, as before.
- **Logout only by button.** `/logout` now accepts POST only, with the CSRF token.
  - A plain link or a typed address can no longer log a user out (GET gives 405).
  - Sidebar "Logout" is now a small form button; it looks the same as before.
- **Cashier privacy (display).**
  - Medicines page: cost price and margin are hidden for Cashier. The edit window does not receive the cost either.
  - Customers page: "Medical History" column and "With History" stat are hidden for Cashier.
  - Prescription page: the medical history stored in the dropdown is empty for Cashier.
  - Admin and Pharmacist see everything as before.

## Files
- Replace: `pharmacy/lib.py`, `pharmacy/core.py` (unchanged content, included for safety), `pharmacy/routes/*.py` (14 files), `templates/base.html`, `templates/medicines.html`, `templates/customers.html`, `templates/add_prescription.html`
- New: `tests/test_step10_security.py` (11 checks)

## Tests
- Full mock suite: 507 pass, 2 fail (the 2 old profile tests, unchanged).
- Step 10 checks: no raw error text in routes, safe message content, GET /logout = 405, wrong token refused, right token logs out, Cashier hides medical history, Admin still sees it, cost hidden from Cashier.

## Pharmacy benefit
- A cashier cannot see what the shop paid for a medicine, or a customer's health history, even by accident on screen.
- Staff cannot be logged out by accident from a link; the owner's login is safer.
- Errors are short and clear at the counter; the technical detail stays with the owner's computer log.

## Not done yet (planned for later parts)
- Content-Security-Policy header: the current pages use inline scripts and styles, so a strict policy would break them. It needs a planned clean-up first.
- Photo upload: extension is checked, but no file size limit and no image content check yet.
- CSV exports and API responses: hiding is on the screen only. Server-side filtering for Cashier is still to be added.
- Profile page tests (2 old failures).

## From CHANGELOG_STEP10_PART2.md

# MediGen AI Pro - Step 10 part 2 (Security finish)

## What changed
- **Medicine CSV export:** the Cost column is blank for Cashier. The cost is removed on the server, not just hidden on screen.
- **Profile photo upload:**
  - Maximum size 2 MB.
  - The file must really be a PNG, JPEG, GIF or WEBP image. A renamed text or script file is refused with a clear message.
- Tests: 16 Step 10 checks (was 11), full suite 543 pass, 0 fail.

## Still planned
- Content-Security-Policy header: needs the inline scripts and styles cleaned up first.

## Files
- Replace: `pharmacy/routes/medicines.py`, `pharmacy/routes/profile.py`, `tests/test_step10_security.py`
- Full project zip also included (safe to replace all files).

## From CHANGELOG_STEP11.md

# CHANGELOG - Step 11 (full project polish and fixes)

## Forgot password (was: text only, nothing clickable)
- Login page: "Forgot password?" is now a real raised button linking to `/forgot-password`.
- New page `/forgot-password` explains the safe reset path (Admin resets from Users).
- Users page: new key icon (Reset Password) for every user except yourself.
- New route `POST /users/reset_password/<id>`: Admin only, login required, password rules enforced,
  stored as bcrypt hash, written to the audit log (`user.reset_password`). The password is never flashed or logged.

## Error handling
- Raw error text is shown only in DEBUG mode. Normal users and the Admin see the friendly 500 page.
  The full error always goes to the terminal log.
- Test `test_step10_security.py` fixed: it added a route after requests had run (Flask refuses that).

## Neumorphism look
- New `static/css/neu.css` (loaded last, cache-busted `?v=11`): raised logout button, raised icon buttons
  in tables, raised forgot-password button, soft focus and reduced-motion support.
- base.html keeps the light neumorphism sidebar. If your screen still shows a DARK navy sidebar,
  your copy of base.html is older than Step 10b. Replace it from this zip and press Ctrl+F5.

## Tests
- New `tests/test_step11_polish.py` (14 checks).
- Full mock suite: 560 passed, 0 failed (`python tests/run_all.py`).

## Not done in this step (honest list)
- The live MySQL test (`python tests/run_all.py --live`) must be run on your PC.
- Backup, Audit Log and Customers pages still use the existing table design; a full redesign of each is a later step.
- Step 6 part 2 (translating every heading and flash message) is not finished.
- Content-Security-Policy header is not added yet (inline scripts and styles must move first).
- Visual check was done by rendering HTML, not in a real browser. Please check each page once after copying.

## From CHANGELOG_STEP11B.md

# CHANGELOG - Step 11b (forgot password feature, embossed sidebar, backup and audit polish)

## Forgot password (now a real feature)
- Admin: Users page, new ticket icon "Make one-time reset code" per user.
  Code looks like `ABCD-EFGH`, is valid 15 minutes, works once, and is shown once on screen.
- Only a SHA-256 hash of the code is stored (new table `password_resets`, created automatically).
- `/forgot-password` form: username, reset code, new password, confirm. Password rules apply.
- After 5 wrong tries the user waits a few minutes (uses the existing login lock).
- Wrong username, wrong code and expired code all show the same message (no username guessing).
- Success and failures are written to the audit log (`password.reset`, `password.reset_failed`).
- Admin "set new password now" (key icon) is still there.

## Sidebar
- Embossed look: raised brand card, raised user card, icon tiles, pressed active item with a glowing bar.
- Section labels with a thin fading line; logout is a raised red-tinted tile.

## Backup and Audit Log
- Raised cards, raised chips and buttons, pressed inputs, brand gradient on main buttons.
- Clearer table headers and row hover; stat cards and status pills match the new look.

## Tests
- `tests/test_step11_polish.py`: 20 checks.
- Full mock suite: 566 passed, 0 failed.

## Still open
- Live MySQL test: run `python tests/run_all.py --live` on your PC.
- Browser check: this was checked by rendering HTML, not in a real browser. Look at each page once after copying (Ctrl+F5).
- Customers page table layout is unchanged except the shared icon buttons.
- Step 6 part 2 translations, Content-Security-Policy header.

## From CHANGELOG_STEP11C.md

# CHANGELOG - Step 11c (dark embossed sidebar)
- Sidebar back to the deep navy MediGen look, with real embossing:
  raised tiles with a dark shadow and a soft light edge, a pressed (inset) user panel,
  a glowing teal logo tile, and icon chips that sit inside the tiles.
- Active menu item is pressed in, with a bright teal icon chip and a glowing side bar.
- Logout is a raised tile with a red accent.
- Light-colour sidebar rules from 11b removed. Backup and Audit styles unchanged.
- Files changed: static/css/neu.css (sidebar section), templates/base.html (stylesheet version ?v=11c).
- Mock suite: 566 passed, 0 failed.

## From CHANGELOG_STEP11D_SPATIAL.md

# CHANGELOG - Step 11d (MediGen Spatial theme, full frontend)

## Look
- Dark aurora background (animated teal, violet and blue light behind the pages). Built into base.html as `.aurora`.
- Floating glass sidebar: rounded, blurred, with a glowing teal active item and a glowing side bar.
- Glass cards everywhere: stat cards, chart cards, tables, modals, login, forgot password, backup, audit, error pages.
- Stat numbers use a white-to-silver gradient with a soft glow. Labels are teal and uppercase.
- Gradient buttons with a glow on hover, a press effect and a ripple on click.
- Inputs are embossed wells that glow teal on focus.
- Tables: transparent rows, teal hover glow, muted uppercase headers.
- Chart.js text and grid colours set for the dark background (spatial.js).

## Motion
- Page fade-in and slide-up on load.
- Cards follow the mouse with a soft light; stat cards tilt in 3D (mouse devices only).
- Users with reduced-motion settings get no animation.

## Files
- NEW static/css/spatial.css (whole theme, loaded last, ?v=12)
- NEW static/js/spatial.js (mouse light, tilt, ripple, chart colours)
- REMOVED static/css/neu.css (replaced by spatial.css)
- CHANGED templates/base.html (aurora div, spatial.css, spatial.js)
- CHANGED templates/404.html and templates/500.html (aurora and theme)
- CHANGED tests/test_step11_polish.py (checks spatial.css and spatial.js)

## Tests
- Mock suite: 566 passed, 0 failed (`python tests/run_all.py`).

## Notes
- Icons come from the Bootstrap Icons CDN. If the PC is offline, run `python scripts/fetch_assets.py` once with internet.
- Checked by rendering pages in headless Chromium with stub data (login, forgot password, dashboard, medicines, customers, batches, backup). Please look at every page on your PC once.

## From CHANGELOG_STEP11E_LIGHT.md

# MediGen AI Pro - Step 11E: Ultra Premium Light Glass Theme

## What changed
- New theme file `static/css/light.css` (replaces `spatial.css` in the page load).
- `templates/base.html`, `404.html`, `500.html` now load `css/light.css?v=13`.
- `static/js/spatial.js`: chart colours now read `--chart-text` from the theme (dark text on light background).
- `tests/test_step11_polish.py`: checks `light.css` is loaded.

## Design
- Icy light background with soft teal and blue glows.
- Glass cards: white, blurred, soft shadows, teal glow on hover.
- Floating light sidebar; active item uses the teal-to-blue gradient.
- Brand gradient on primary buttons, stat numbers and focus rings.
- Inputs: light wells with a teal focus ring.
- Tables: light header, readable dark text, soft row hover.
- Login, forgot password, backup, audit and error pages all use the light theme.
- Mobile: sidebar becomes a glass drawer.

## Notes
- `spatial.css` is no longer linked. It can be deleted safely.
- `static/css/neu.css` should not exist. Delete it if it is still in your folder.
- Icons come from Bootstrap Icons CDN. Use `scripts/fetch_assets.py` for offline use.

## Install
1. Replace the whole project folder (or copy `static/css`, `static/js`, `templates`, `tests`).
2. Restart: `python app.py`.
3. Press Ctrl+F5 in the browser.
4. Run `python tests/run_all.py --live` on your PC.

## From CHANGELOG_STEP11F_BENTO.md

# MediGen AI Pro - Step 11F: Bento Grid + Spatial Depth + Animated Mesh

## What changed
- New `static/css/bento.css` (?v=14), loaded after `light.css`.
- `templates/base.html`: adds `<div class="mesh-bg">` (animated background) and links `bento.css`.
- `templates/dashboard.html`: stats, charts and alerts now use a 12-column bento grid.
  - Today's Revenue is a large hero tile (2 rows).
  - Medicines and Customers are small tiles; Today's Sales is a wide tile.
  - Sales chart is 8 columns, Top 5 chart is 4 columns.
  - Alerts and Quick Actions are three equal tiles.
- Chart.js is pinned to `chart.js@4.4.1` (was unversioned).
- New test `tests/test_step11f_bento.py` (15 checks).

## Design
- **Animated mesh gradient:** four soft blurred colour blobs (teal, blue, lavender, peach) drift slowly behind the page.
- **Bento grid:** tiles of different sizes, responsive at 1100px and 640px.
- **Spatial depth:** layered shadows, hover lift, and numbers and headings floating above the glass (`translateZ`). Mouse-follow tilt and spotlight from `spatial.js` still work.
- **Entrance animation:** tiles fade in one after another.
- **Motion:** all animation is turned off when the user prefers reduced motion.

## Notes
- Bento is applied to the dashboard. Other pages keep the Light Glass layout with the mesh background.
- `spatial.css` and `neu.css` are not linked and can be deleted.

## Install
1. Replace the project folder (or copy `static/css`, `static/js`, `templates`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 581 passed).

## From CHANGELOG_STEP11G_SLATE.md

# MediGen AI Pro - Step 11G: Soft Slate Neumorphic Enterprise Theme

## Design
- Mid-tone slate surface (`#dde3eb`). Not too light, not too dark.
- Raised neumorphic cards, sidebar and buttons. Pressed (inset) inputs and active nav items.
- Deep slate text, muted teal and slate-blue accents. No neon, no glow.
- Same layout and components as before; only colour, depth and surfaces changed.

## base.html (full file, fixed)
- Clean structure: `<aside class="sidebar">`, `<main class="main-content">`, `<header class="top-bar">`.
- Inline `style=` attributes removed. Top bar uses classes `lang-form` and `lang-btn`.
- All theme CSS is linked, in order: `light.css` -> `bento.css` -> `enterprise.css` -> `slate.css` (last, wins).
- All theme and script files bumped to `?v=17` so browsers load the new CSS.
- `<html lang>` follows the language setting.
- Sidebar links, admin/role rules, mobile menu, data-method POST links and the greeting are unchanged.
- Nav order is unchanged.

## Other
- `static/css/slate.css`: top bar helper classes added.
- `static/css/bento.css`: dead mesh background removed. Bento grid gets its own bottom spacing (does not rely on Bootstrap utilities).
- Tests updated for the new structure (CSS layers instead of inline style block; mesh checks removed). `tests/run_all.py`: 578 passed, 0 failed.

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py`.

## Notes
- `spatial.css`, `neu.css` and `style.css` (legacy) are not linked by base.html. Delete `neu.css` if it is still in your folder.

## From CHANGELOG_STEP11H_ULTIMATE.md

# MediGen AI Pro - Step 11H: Ultimate Enterprise Layer

## What it is
A final layer on top of the slate theme. One palette (slate, one muted teal accent), no neon, no brutal borders, no colour shifts.

Design ideas used (from the reference list):
- Neumorphic spatial depth: slate.css tokens, raised and pressed surfaces.
- Bento grid: dashboard tiles (bento.css), hairline highlight and sheen on cards.
- Glassmorphism (Windows 11 Mica / visionOS): frosted top bar and sidebar.
- Claymorphism: soft inflated icon tiles in the sidebar.
- Minimalist monochrome (Linear / Vercel): dark-slate primary buttons, one accent for active state and focus.
- Aurora (Stripe): very faint teal and blue glow in the background.
- Swiss grid (IBM): faint hairline grid, tabular numerals, tight tracking, uppercase labels.

Not used: brutalism and cyberpunk neon (out of scope for this app), Material You colour shifts (would change colours).

## Files
- NEW `static/css/ultimate.css` (v18): tokens, background texture, Mica chrome, typography, bento cards, nav, clay icons, buttons, tables, inputs, focus ring, reduced motion.
- NEW `static/js/ultimate.js` (v18): count-up for plain whole-number stat tiles only. Skipped for zero, for currency text and when reduced motion is on.
- `templates/base.html`: links `ultimate.css` last; loads `ultimate.js` after `spatial.js`. All theme files bumped to `?v=18`.
- NEW `tests/test_step11h_ultimate.py` (9 checks).

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `static/js`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 587 passed).

## From CHANGELOG_STEP11I_TACTILE.md

# MediGen AI Pro - Step 11I: Hyper-Minimal Tactile 3D Layer

## What changed (vs Ultimate 11H)
- Background is calm: the hairline grid and aurora are removed (`body::before` off). One solid surface.
- Cards have three real elevation levels: rest, hover (lifts 2px) and pressed (sinks).
- Primary buttons are physical keys: a visible lip under the button, the key travels down when pressed.
- Secondary buttons are raised keys with a pressed state.
- Sidebar active item is a pressed key (inset shadow), no gradient.
- Inputs are pressed wells with a soft inner edge.
- Tables have more breathing room; row hover is a soft white wash.
- Bento gap is 20px (16px on small screens).

## Files
- NEW `static/css/tactile.css` (v19), loaded last.
- `templates/base.html`: links `tactile.css?v=19`. All theme files bumped to `?v=19`.
- NEW `tests/test_step11i_tactile.py` (5 checks).

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 592 passed).

## From CHANGELOG_STEP11J_PROFESSIONAL.md

# MediGen AI Pro - Step 11J: Professional Clean Layer

## What changed (vs silver/grey Tactile 11I)
- Silver and grey surfaces removed. Canvas is ice-blue (#f4f7fb), cards and sidebar are white.
- Deep navy text, one muted blue accent (#1d5fa7) for primary buttons, active nav, focus and icons.
- Crisp 1px borders with short, soft shadows. No grey relief, no inner shadows.
- Frosted glass removed for a clean look. Hairline grid and aurora stay off.
- Alerts, tables, inputs and secondary buttons follow the same system.

## Files
- NEW `static/css/professional.css` (v20), loaded last.
- `templates/base.html`: links `professional.css?v=20`. All theme files bumped to `?v=20`.
- NEW `tests/test_step11j_professional.py` (6 checks).

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 598 passed).

## From CHANGELOG_STEP11K_PROFESSIONAL_PLUS.md

# MediGen AI Pro - Step 11K: Professional Plus

Same white, ice-blue and navy system as 11J, with more polish.

## Changes
- Sidebar: solid accent icon chips; active item uses a filled chip; navy "AI Pro" badge; gradient logo and avatar.
- Top bar: thicker gradient accent line, stronger title.
- Stat and chart cards: accent icon chips next to headings; the watermark icon is removed.
- Revenue hero card: soft white-to-ice gradient with navy number.
- Quick actions: icon chips, cleaner spacing.
- Buttons: accent gradient with a light top edge.
- Tables: uppercase headers, more row padding, soft row hover.
- Login: branded navy-blue panel and deeper card shadow.

## Files
- NEW `static/css/professional2.css` (v21), loaded last.
- `templates/base.html`: links `professional2.css?v=21`. All theme files bumped to `?v=21`.
- NEW `tests/test_step11k_professional2.py` (5 checks).

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 603 passed).

## From CHANGELOG_STEP11L_CLASSIC.md

# MediGen AI Pro - Step 11L: Back to the Original Look (Step 1 design)

## What changed
- The look is restored from the original Step 1 design: navy sidebar with gradient brand tile, white cards with coloured top accents, light canvas and teal/blue gradients.
- All theme layers from 11D to 11K are removed from the page: light, bento, enterprise, slate, ultimate, tactile, professional, professional2, spatial.
- `static/css/classic.css` (v22) is the only theme stylesheet. It holds the original Step 1 CSS, plus a small grid for the dashboard (bento classes used by dashboard.html).
- `templates/base.html`: links `classic.css?v=22` only. Effect scripts `spatial.js` and `ultimate.js` are no longer loaded. Structure, navigation, roles, mobile menu and POST links are unchanged.
- Unused files removed: the theme CSS and JS listed above, and `neu.css`.
- Tests: obsolete layer tests removed (11F, 11H, 11I, 11J, 11K). Remaining tests now check `classic.css`. `tests/run_all.py`: 566 passed, 0 failed.

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `static/js`, `tests`).
2. Delete `static/css/light.css`, `bento.css`, `enterprise.css`, `slate.css`, `ultimate.css`, `tactile.css`, `professional.css`, `professional2.css`, `spatial.css`, `neu.css`, and `static/js/spatial.js`, `ultimate.js` if they are still in your folder.
3. `python app.py`, then Ctrl+F5.
4. `python tests/run_all.py` (expect 566 passed).

## From CHANGELOG_STEP11M_PAGES.md

# MediGen AI Pro - Step 11M: Audit and Backup Page Styles (full project)

## Why
In 11L the theme layers were removed, and the audit (au-*) and backup (bk-*) classes lost their styles. This step adds them back in a clean, professional form.

## Changes
- NEW `static/css/pages.css` (v23), scoped to `au-*` and `bk-*` classes.
  - Audit log: header with actions, five stat cards with coloured top accents, filter chips, a filter panel that fits on one row, a clean table with uppercase headers, action and result pills, pager, and the detail modal.
  - Backup: cards with a soft header, a clean backup table with monospace file names, a warning banner, inputs and buttons.
- Customers page is unchanged (its own inline styles were already correct).
- `templates/base.html`: links `pages.css?v=23` after `classic.css`. Both files are at v=23.
- NEW `tests/test_step11m_pages.py` (16 checks).
- Tests: 582 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 582 passed).

## From CHANGELOG_STEP11N_CUSTOMERS_FIX.md

# MediGen AI Pro - Step 11N: Customers Table Fix

## Problem
On the Customers page the table was wider than its card, so the Action column (delete button) was cut off at the right edge.

## Fix (CSS only, in `static/css/pages.css` v24)
- `.data-card` scrolls horizontally when needed instead of clipping.
- `.data-table` has a minimum width of 860px, so every column stays readable.
- The Action column has enough right padding and does not wrap.
- Action button design is unchanged. No template changes.

## Audit and backup
Kept as they are (already styled in 11M). Both pages look professional.

## Verified
- At 1440px the table fits inside the card, and the last column ends inside the card edge.
- At 1024px the card scrolls, so the Action column is reachable and not clipped.
- Tests: 584 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 584 passed).

## From CHANGELOG_STEP11O_REMOVE_AUDIT_BACKUP.md

# MediGen AI Pro - Step 11O: Audit Log and Backup Removed

## Removed from the project
- Audit Log page (`/audit`, export and timeline), its templates, and its route file.
- Backup page (`/backup`, create, download, restore, delete), its templates, and its route file.
- Root `backup.py` module (dump, restore and auto-backup helpers).
- Daily automatic backup at start-up in `app.py` and `desktop.py`.
- Sidebar links for Backup and Audit Log.
- Audit Log link on the Reports page.
- Backup and audit statistics on Settings (backups count, audit protected tile).
- Audit and backup wording in profile, settings, and the 500 error page.
- Audit and backup styles in `pages.css` (only the customers table fix remains).
- Obsolete tests, and the backup/restore part of the live MySQL test.

## Kept on purpose
- The `audit_log` table, its append-only database triggers, and the internal `audit()` calls in sales, medicines, users and other routes. These run inside business transactions. Removing them touches almost every route. If you want those removed too, tell me and I will do it as a separate step.

## Verified
- `/backup` and `/audit` return 404.
- Sidebar, Reports and Settings have no audit or backup links.
- Tests: 499 passed, 0 failed (mock suite). The live MySQL test was updated but not run in this sandbox.

## Install
1. Replace the whole project folder. Delete the old `backup.py` and `templates/backup.html`, `audit_log.html`, `audit_timeline.html` if they remain.
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 499 passed).

## From CHANGELOG_STEP11P_CUSTOMERS_ACTION_FIT.md

# MediGen AI Pro - Step 11P: Customers Action column fits on screen

## Changed
- `static/css/pages.css` (v25): removed the forced 860px table width, so the table fits the card.
  Cell side padding reduced slightly (12px), email cells wrap, and the Action column keeps its right padding.
- `templates/base.html`: pages.css cache version bumped to v=25.

## Not changed
- Customer action buttons (delete button and its look), customer modal and the rest of the page.

## Install
1. Replace the project folder (or copy `static/css/pages.css` and `templates/base.html`).
2. `python app.py`, then Ctrl+F5 in the browser.
3. `python tests/run_all.py` (499 passed).

## From CHANGELOG_STEP12_README_UPDATE.md

# MediGen AI Pro - Step 12: README updated after audit and backup removal

## Changed
- README.md: Settings and backup section is now "Settings" only. Backup and restore steps removed.
- README.md: Audit log developer section removed.
- README.md: .exe notes no longer mention the `backups` folder. Use MySQL backup instead.
- README.md: live test description and the audit_log note updated.
- app.py: module docstring no longer mentions backup.

## Not changed
- All code behaviour, customers page and tests (499 passed).

## Install
1. Replace the project folder, or copy README.md and app.py.
2. `python app.py`, then Ctrl+F5.

## From CHANGELOG_STEP13_FINAL_HARDENING.md

# Final hardening (v34 -> v35)

## What changed
- **Exception safety on every route**: new `guarded()` decorator in `pharmacy/lib.py`, applied to all 69 routes.
  - Unexpected errors are logged in full on the server.
  - The database transaction is rolled back.
  - Users see a short message: a 500 page for normal pages, a JSON error for `/api/` and `/chatbot/api`, and a flash message plus redirect for failed form posts.
  - Form-post redirects only go back to pages on this same site (no redirect to other websites).
  - Normal HTTP errors (404, 401, redirects) pass through unchanged.
- **Security fix**: the stock history table on the medicine page now escapes the note, reason, user and date fields before showing them (stored XSS guard).
- **Desktop app**: if the browser cannot open automatically, the app now prints the address to open by hand.
- **Logging**: the shop-name fallback in reports now logs the error.

## Tests
- `tests/test_guarded.py` (5 tests): friendly 500, POST flash/redirect, no external redirect, HTTP errors pass through, JSON errors for API.
- `tests/test_history_escape.py` (3 tests): escape guard for stock history.
- Full suite: 1036 passed, 0 failed (with the mock database).

## Still needs the real PC
- Live MySQL test (`python tests\run_all.py --live`)
- Android APK build and phone test
- Mobile-data test of the internet link

## From CHANGELOG_STEP14_WORD_EXPORT_CHECKS.md

# Word export, live test fix and static checks (v36 -> v37)

## Added
- Sales report can be downloaded as Word (.docx): new "Word (.docx)" button in Reports > Daily Sales Breakdown.
  - File has: title, period, summary figures, a table with a shaded header row (repeats on each page), and notes.
  - Uses python-docx (added to requirements.txt). Run `python -m pip install -r requirements.txt` once.
- `build_docx()` in `pharmacy/exports.py`; `export_report` accepts `fmt=docx`.

## Fixed
- Live MySQL test: every POST now sends a real CSRF token (the test had fake tokens, so login was rejected and every page redirected).
- Live test no longer depends on the HTTPS_ONLY setting in .env (test-only setting).
- 404 and 500 error pages linked to `css/light.css`, which does not exist. Link removed.

## Checks added
- `tests/test_docx_export.py` (6): the Word file opens, table/summary/notes are correct, button and route present.
- `tests/test_static_refs.py` (2): every static file a template links to exists.

## Checked, no problem found
- All 70 `url_for` targets in templates and Python exist as routes.
- All fetch() URLs in JavaScript match a route (the one flagged was a false alarm).

## Not checked here
- Live MySQL test (no MySQL in the build sandbox). Run `python tests\run_all.py --live` on the shop PC.
- Real AI (Gemini, OpenAI, Claude) needs an API key and internet; only the mock tests run here.

## From CHANGELOG_STEP15_LIVE_TEST_ROOT_CAUSE.md

# Live test root cause, old test files, admin name (v38 -> v39)

## Root cause of the live test login failure
- `config.py` reads DB_NAME, DB_HOST, DB_USER and DB_PASSWORD once, when it is first imported.
- The live test set DB_NAME to `medigen_live_test` AFTER importing config.
- So the app connected to the real `pharmacy_management_system` database, where the test user does not exist.
- Result: login failed and every page redirected to login (302).
- Fix: the test sets its environment variables BEFORE importing config, and asserts that the database name is the test database.
- Earlier test-only fixes stay: real CSRF tokens on every POST, and no dependence on HTTPS_ONLY.

## Note for the real database
- The failed live-test logins may have written a `login.fail` line to the real audit log. The audit log is append-only by design, so that line stays. It is harmless.

## Old test files
- `scripts/remove_old_test_files.py` deletes exactly the 12 old test files that are not part of this version.
- Run it once, then copy the `tests` folder from this zip.

## Admin name
- `database/rename_admin.sql` changes the Admin account named `Ahmed` to `Admin: CEO`. Run it in the MySQL client with `source database/rename_admin.sql`.

## Results here
- Mock suite: 1044 passed, 0 failed.
- Live MySQL test: not run here (no MySQL in the sandbox). Run `python tests\run_all.py --live` on the shop PC.

## From CHANGELOG_STEP16_PROFILE_SAVE_FIX.md

# Profile save fix and missing-column migration (v39 -> v40)

## Cause
- Databases made from an older schema were missing some columns in the `users` table (for example `position`, `honors`, `about`, `access_start_time`).
- The profile save writes those columns, so MySQL answered "Unknown column", and the app showed "Could not save your profile".
- `ensure_schema()` only added missing columns for `sales` and `audit_log`, not for `users`.

## Fix
- `ensure_schema()` now adds every missing `users` profile and access column automatically the first time the app starts. Each added column is logged.
- Future schema changes: add the column to the list in `ensure_schema()` (USER_COLUMNS), and the test `tests/test_user_columns_migration.py` checks it.

## Tests
- `tests/test_user_columns_migration.py` (3 tests): every profile field has an auto-add, access and picture columns are covered, the migration runs during schema setup.
- Full mock suite: 1047 passed, 0 failed.

## Settings page
- Checked the save code: uses `app_settings` (created automatically, primary key on setting_key). No change needed.

## Still to check on the shop PC
- Restart the server once (so the migration runs), then save My Profile again.
- Look at `logs\server.log` for "Added missing users.<column> column" lines.

## From CHANGELOG_STEP17_NAME_SYNC.md

# Name and role follow the database (v40 -> v41)

## Problem
- A name changed in My Profile or on the Users page was saved in the database, but the sidebar, the dashboard and the "Welcome back" line kept the old name.
- The name was stored in the login session and only refreshed at the next login.

## Fix
- `_sync_session_user()` (before every request, in `pharmacy/core.py`) reads the user's name and role from the database and updates the session.
- If the account is deactivated, the user is logged out at once.
- If the database gives no answer, the session is kept (the page still opens).
- Known limit: a deleted account's session ends after the idle timeout (30 minutes).

## Test fakes updated
- `test_business_step5`, `test_step10_security`, `test_coverage_admin`: fake databases now return the role for the user id, like the real database. The cashier test uses user id 3.

## Tests
- `tests/test_session_sync.py` (4 tests).
- Full mock suite: 1047 passed, 0 failed.

## From CHANGELOG_STEP18_USER_DELETE_FIX.md

# Step 18 - User delete and reset-code fixes (v48)

## Problem
- A user with sales or chatbot history (for example "hassain") could not be deleted.
  `sales.user_id` and `chat_history.user_id` point to `users`, and the delete had no rule for them.
  MySQL refused the delete, and the error was hidden behind "Something went wrong".

## Fix
- `delete_user` (pharmacy/routes/users.py) now checks the history first:
  - No sales and no chat history: the user is deleted (login tokens and reset codes removed first).
  - Has sales or chat history: the user is turned OFF (is_active = 0), history is kept, and the admin sees the reason.
- Real database errors are logged in full and rolled back. A foreign-key error shows a clear message.
- Audit log records `user.delete` or `user.deactivate`.

## Forgot password
- The flow is: Admin presses "Make one-time reset code" on the Users page, the user types it on the
  Forgot password page (valid 15 minutes, one use). Code and page were checked and match.
- Admin can also press "Set new password now" (key icon) to set a password immediately.

## Tests
- `tests/test_coverage_admin.py`: delete with no history, and deactivate with history.
- `python tests/run_all.py`: 1073 passed, 0 failed (mock database).
- Not run here: the live MySQL test (`--live`) and the Windows build. Run them on the shop PC.

## From CHANGELOG_STEP19_SALE_SAFETY.md

# Step 19 - Sale safety (backend)

## Changed
- `pharmacy/routes/sales.py` (new sale):
  - A medicine that was deleted after the page loaded is no longer dropped silently.
    The whole bill is rejected with: "A selected medicine no longer exists. Please reload the page and try again."
  - Medicine rows are locked in a fixed (id) order, so two sales that contain the same medicines cannot deadlock.
  - Non-numeric medicine ids are rejected ("Invalid medicine selected").
  - A bill is limited to 100 different medicines.

## Tests
- `tests/test_coverage_sales_lib.py`: unknown-medicine message updated; new checks for partial-missing bill,
  non-numeric id, and fixed lock order.
- Result: 1076 passed, 0 failed (mock database). Run `python tests\run_all.py --live` on the shop PC with MySQL.

## From CHANGELOG_STEP2.md

# MediGen AI Pro - Step 2 (structure)

## What changed
- `app.py` is now a short start-up file (about 70 lines). It starts the app and keeps the start-up checks.
- All code moved into the `pharmacy/` package:
  - `pharmacy/core.py`: Flask app, database handle, CSRF, login lock, schema checks, login and role decorators.
  - `pharmacy/lib.py`: shared helpers (settings, audit log, prescription checks, reports, chat, backup helpers).
  - `pharmacy/routes/`: one file per area: auth, dashboard, medicines, batches, catalog (categories, customers, suppliers), sales, purchase, prescriptions, audit, reports, users, chatbot, profile, records, settings, backup, errors.
- No URL, page name or form field changed. All 64 routes match the previous version exactly.
- `desktop.py`, `build_exe.bat` and `MediGen_AI.bat` work without changes (they still start `app`).

## Tests
- Mock suite: 349 pass, 2 fail. The 2 failures were there before (profile tabs and profile-update audit).
- Two tests read `app.py` as text. They now read the `pharmacy/` files too. One test sets a module value that moved (`BACKUP_DIR`, `_schema_ready`) and now sets it where the code reads it.

## Files to put in the project
- Replace: `app.py`, `tests/test_audit_log.py`, `tests/test_settings_backup.py`.
- New folder: `pharmacy/` (copy the whole folder, keep the `routes` sub-folder).
- Keep as before: `config.py`, `backup.py`, `chatbot_engine.py`, `templates/`, `static/`, `database/`.

## Not changed yet
- Repository (data) layer: Step 3.
- Templates and CSS: Steps 6 and 7.

## From CHANGELOG_STEP20_PRODUCT_IMPORT.md

# Step 20 - Product import, backup restore helper, frontend freeze (backend track, v49)

## Added
- `pharmacy/services/product_import.py`: reads CSV/XLSX product lists, checks every row (prices, barcode, dates,
  whole numbers, placeholders), builds a plan (create / update / skip / error), and writes it in one transaction.
  - Rules: all-or-nothing; placeholders ("Verify...", "N/A") become NULL; Rx "Yes"/"No" only, unclear = NULL;
    existing stock is never changed by import; every new medicine gets an audit row.
- `scripts/import_products.py`: dry run by default; `--commit` writes; `--update-existing`; writes a report CSV.
- `scripts/docx_products_to_csv.py`: converts the 230-product Word master list to CSV.
- `database/samples/`: the 230-product docx and the converted CSV (demo data, not verified stock).
- `scripts/restore_backup.py`: restores a Workbench backup folder into a NEW check database (never the live one).
- `docs/RESTORE_AND_IMPORT_STEPS.md`: step-by-step guide in Roman Urdu.
- `tests/test_product_import.py`, `tests/test_restore_backup.py`: 44 + 6 checks, no MySQL needed.
- `tests/test_backend_freeze.py` + `tests/frontend_manifest.json`: fails if any template or static file changes.

## Changed
- `pharmacy/core.py` `ensure_schema()`: adds product columns to `medicines` when missing (product_code, generic_name,
  manufacturer, strength, dosage_form, pack_size, rack_location, rx_required, schedule, tax_rate, import_source),
  and tries a unique index on `barcode` (logs a warning if old data has duplicates).

## Not changed
- templates/ and static/ (checked by the freeze test). No route, URL or JSON shape changed.

## Not tested here
- Real MySQL: this environment has no MySQL server. Run `python tests\run_all.py --live` on the shop PC, and the
  restore steps in docs/RESTORE_AND_IMPORT_STEPS.md against the check database first.

## From CHANGELOG_STEP21_DOUBLE_SUBMIT.md

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

## From CHANGELOG_STEP22_MIGRATIONS.md

# Step 22 - Numbered schema migrations (backend track, B2, v49.2)

## Added
- `pharmacy/services/migrations.py`: runs `database/migrations/NNN_name.sql` files in number order.
  Each file runs once; the number is stored in the `schema_version` table. A failing file stops the run
  and is not recorded as applied. Two files with the same number are refused.
- `database/migrations/002_sale_guard.sql`: the `sale_guard` table (moved here from the B1 code).
- `tests/test_migrations.py`: 13 checks (file rules, order, run once, stop on error, project file).

## Changed
- `pharmacy/core.py` `ensure_schema()`: calls `run_migrations(cur)` at startup.

## Not changed (on purpose)
- Column changes stay in the existing startup checks in `ensure_schema()`. MySQL 8 has no
  `ADD COLUMN IF NOT EXISTS`, so they are not safe as plain migration files yet. Move them over one at a time,
  after each is tested on a copy of the shop database.
- Templates and static files (freeze test passes).

## Tests
- Result: 1165 passed, 0 failed (mock database).

## Not tested here
- Real MySQL: run `python tests\run_all.py --live` on the shop PC. On the check database, confirm
  `SELECT * FROM schema_version;` shows version 2 (sale_guard) after the first start.

## From CHANGELOG_STEP23_SALES_SERVICE.md

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

## From CHANGELOG_STEP24_LIVE_BACKEND.md

# Step 24 - Live backend tests on real MySQL (backend track, B4, v49.4)

## Added
- `tests/test_live_backend.py` (runs only with `run_all.py --live`): on a scratch database `medigen_live_test`,
  it checks:
  - schema_version records migration 002, and a second run applies nothing;
  - product columns and the unique barcode index exist;
  - product import: dry run has no errors, commit creates one medicine and one batch per new product,
    existing items keep their stock, and a second import creates nothing;
  - double submit on a real sale saves exactly one sale;
  - the audit log triggers exist.

## Changed
- `tests/run_all.py`: `--live` runs both live files (`test_live_mysql.py`, `test_live_backend.py`); without
  `--live` both are skipped.

## Not tested here
- The live test was written in a sandbox that has no MySQL server or MySQL client library, so it has NOT been
  run. Expect small SQL or fixture fixes on the first real run. Run:
  `python tests\run_all.py --live` on the shop PC (or a PC with MySQL 8) and send me the output.

## From CHANGELOG_STEP25_INVENTORY.md

# Step 25 - Inventory automation: expiry buckets, low-stock severity, purchase suggestions (backend track, B7, v49.5)

## Added
- `pharmacy/services/inventory.py` (pure rules):
  - `expiry_buckets`: expired, 0-30, 31-60, 61-90 days (batches expiring after 90 days are left out).
  - `low_stock`: severity `out` (0 in stock), `critical` (below half the reorder level), `low` (at reorder level).
  - `purchase_suggestions`: order up to twice the reorder level, grouped by the supplier of the latest received
    purchase; medicines with no purchase history go under "No supplier history".
- `scripts/inventory_report.py`: daily report, read-only. Writes `expiry_buckets.csv`, `low_stock.csv`,
  `purchase_suggestions.csv` and `summary.txt` into `reports\YYYY-MM-DD\` (or `--out`).
- `tests/test_inventory.py`: 10 checks.

## Scheduling (Windows Task Scheduler, no code needed)
- Program: `python`; arguments: `scripts\inventory_report.py`; start in: the project folder; daily at 08:00.

## Not included yet
- Stock count sessions with variance approval (larger change, next step).
- Sending the report by WhatsApp or email.

## Not changed
- Templates and static files (freeze test passes). The existing Alerts page and its 90-day check still work as before.

## Tests
- Result: 1201 passed, 0 failed (mock database).
- The report script's database queries are not run by the tests. Run it once on the check database:
  `python scripts\inventory_report.py` and check the four files.

## From CHANGELOG_STEP26_STOCK_COUNT.md

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

## From CHANGELOG_STEP27_PHASE2_BACKEND.md

# Step 27 - Phase 2 backend: hold and resume bills, phone search (v49.7)

## Added
- `database/migrations/004_held_bills.sql`: `held_bills` table (counter number, user, customer, JSON payload,
  status open / resumed / discarded / expired).
- `pharmacy/services/held_bills.py`:
  - hold a bill at a counter (1 to 20); at most 10 open holds per counter;
  - list open holds; resume once (the bill comes back as data); discard;
  - `expire_old_holds` marks holds older than 24 hours as expired (run from the daily job).
  - Holding does NOT reserve stock. Completing the resumed bill runs the normal stock check.
- `pharmacy/services/phone_search.py`:
  - normalises 0300-1234567, +92 300 1234567, 00923001234567, 3001234567 to the same digits;
  - searches customers by phone, shows the last sale date and the balance owed; needs at least 4 digits; max 50 results.
- `tests/test_phase2_backend.py`: 22 checks.

## Not included yet
- Screens for hold, resume and phone search (frontend track). The services are ready for them.
- Receipt JSON for the thermal printer: the 80mm receipt template already exists.

## Not changed
- Templates and static files (freeze test passes). No route or URL changed.

## Tests
- Result: 1247 passed, 0 failed (mock database).
- Not run on real MySQL yet. The SQL for phone search uses REPLACE and LIKE; check it on the check database with a real number.

## From CHANGELOG_STEP28_PHASE4_COMPLIANCE.md

# Step 28 (v49.8): Phase 4 backend, compliance (register, prescription rule, cold chain)

Backend only. No template or static file changed (freeze test passes).

## What changed
1. Migration `005_controlled_register.sql`: table `controlled_register` (one row per batch part sold of a scheduled medicine).
2. Migration `006_temperature_logs.sql`: table `temperature_logs` (location, temperature, in_range flag, user, note).
3. `pharmacy/services/controlled_register.py`:
   - `scheduled_items`: medicines whose `schedule` is set by the pharmacist.
   - `prescription_missing`: scheduled medicine on a bill with no prescription is refused.
   - `entries_for_sale` / `write_entries`: one register row per batch part.
   - `ensure_register_triggers`: append-only (UPDATE and DELETE blocked). If the DB user lacks TRIGGER permission, the app logs a warning and still starts.
4. `pharmacy/services/temperature.py`: reading parser (accepts `5.2` or `5,2`, rejects non-numbers and impossible values), range check 2.0 to 8.0 C by default, reading saved even when out of range (`in_range = 0`).
5. `pharmacy/services/sales.py`: `check_scheduled` (runs after stock is reserved, before the bill is saved); `save_sale(..., scheduled=None)` writes register rows only when scheduled items exist.
6. `pharmacy/routes/sales.py`: calls `check_scheduled` and passes `scheduled` to `save_sale`. No other route change.
7. `pharmacy/core.py`: imports and calls `ensure_register_triggers` after the migrations.
8. `tests/test_phase4_backend.py`: 29 mock checks.

## Behaviour change to know about
- A medicine with NO schedule value behaves exactly as before.
- A medicine WITH a schedule value now needs a prescription on the bill (`prescription_id`). The sale is refused with: "Prescription needed for: <name>. Attach the prescription to this bill."
- The pharmacist sets `medicines.schedule`. Until it is set, nothing changes.

## Not confirmed (needs the pharmacist / drug authority)
- Which medicines are controlled, and the schedule names.
- The official register layout and retention period.
- Whether buyer identity (CNIC, address) must be recorded. The table currently stores customer_id only; it does not store CNIC.
- Cold-chain range per product. Default 2 to 8 C applies to all locations.

## Tests
- `python tests/run_all.py`: 1276 passed, 0 failed (mock DB).
- Not yet run against real MySQL. Live checks (register triggers, FOR UPDATE on schedule lookup, migration 005/006 creation) need `python tests/run_all.py --live` on the shop PC with a server.

## Not in this step
- Screens for the register and temperature log (frontend parked).
- Daily report lines for temperature out-of-range (planned, not built).

## From CHANGELOG_STEP29_LIVE_PHASE2_4_AND_COLD_CHAIN_REPORT.md

# Step 29 (v49.9): live checks for Phase 2-4 SQL, cold-chain lines in the daily report

Backend only. No template or static file changed.

## What changed
1. `tests/test_live_backend.py` (run with `--live` on a real MySQL server, database `medigen_live_test` only):
   - Held bill: hold, listed as open, resume returns the held lines, second resume refused.
   - Phone search: a customer saved as `0300-7654321` is found by `7654321`; too-short search returns nothing.
   - Stock count: start, count one medicine at +5, submit, approve as Admin; stock equals counted value; a `stock_adjustments` row with reason `Stock count` exists.
   - Controlled register: a scheduled medicine without prescription is refused; a register row written; UPDATE is rejected by the trigger.
   - Temperature: 9.5 C is saved with in_range = 0.
2. `scripts/inventory_report.py`: `summary.txt` gets a cold-chain line: count of readings out of range in the last 24 hours, with each location and time. If migration 006 is not applied, the line says the log is not available yet. The report stays read-only.

## Tests
- `python tests/run_all.py`: 1276 passed, 0 failed (mock DB). The live file is skipped without `--live`.
- Live run: NOT executed (no MySQL in the build environment). The first real run may show small SQL fixes; send the output.

## Known assumptions the live run will confirm
- `customers` columns: name, contact_number.
- `stock_adjustments` columns as used by `approve_count`.
- Trigger on `controlled_register` (created by `ensure_register_triggers` in `ensure_schema`).

## From CHANGELOG_STEP3.md

# MediGen AI Pro - Step 3 (data layer, part 1)

## What changed
- New folder `pharmacy/repos/`: plain SQL functions that take a cursor. No Flask code in this folder.
  - `repos/medicines.py`: medicine list and paging, stats, duplicate-name check, insert, update, FIFO batch removal, stock adjustment rows, stock history, delete, CSV export rows, category list.
  - `repos/catalog.py`: categories, customers, suppliers (list, add, delete, category usage check).
- `pharmacy/routes/medicines.py` and `pharmacy/routes/catalog.py` now call these functions. They have no raw SQL any more.
- SQL text is unchanged, so the database work is the same as before.
- Routes still decide commit and rollback. Flash messages, redirects and role checks are unchanged.
- Small change: the medicine list now checks the filter name once, and the stock history limit (15) is a query parameter.

## Not moved yet (still SQL inside routes)
- Sales, purchase, batches, prescriptions, users, audit, reports, profile, records, backup.
- These follow in the next step (Step 3 part 2), so each area moves with its own tests.

## Tests
- Full mock suite: 376 pass, 2 fail. The 2 failures are the old profile ones (same as Step 2).
- New `tests/test_repos.py` (27 checks): paging and clamping, filters, FIFO batch order, lock clauses, duplicate-name rule when editing, insert order, NULL-safe stats, and a check that the two route files have no raw SQL.
- URL map: 64 routes, identical to the single-file version.

## Files to put in the project
- Replace: `pharmacy/routes/medicines.py`, `pharmacy/routes/catalog.py`.
- New folder: `pharmacy/repos/` (copy the whole folder).
- New test: `tests/test_repos.py`.
- Everything else stays the same.

## From CHANGELOG_STEP30_V52_DASHBOARD_BACKEND.md

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

## From CHANGELOG_STEP31_V53_PROFESSIONAL_UI.md

# Step 31 (v53): professional silver theme and AI assistant panel (FRONTEND change, on purpose)

First intentional frontend change since the freeze. Manifest refreshed with `python tests/test_backend_freeze.py --write`.

## Changes
1. `static/css/pro.css` (new, loaded last in base.html):
   - Silver page background (#d9dfe7 to #cdd5e0), white cards with light border and shadow.
   - Thin sidebar scrollbar.
   - Assistant panel styled like the approved mockup: navy-to-teal header, robot logo, green online dot, round X button, 18px corners.
   - Launcher: pill with a robot badge and "AI Assistant" label.
   - Mobile: panel fills the width, 72% height.
2. `templates/base.html`:
   - Assistant panel (bottom right). X closes it to the launcher. Open or closed state is remembered in this browser (localStorage with try/catch). Default: open on wide screens, closed on phones.
   - Auto-collapse to the launcher after 3 minutes with no activity, in the page and inside the chat iframe. It never collapses while a question is typed. Chat history is kept.
   - `embed-mode` hides the sidebar and top bar when `?embed=1` is used (chat page inside the panel).
3. No backend route, SQL or service changed.

## Tests
- `python tests/run_all.py`: all pass (manifest refreshed).
- Templates parse; frontend tests pass.
- NOT checked in a real browser with the live database.

## Known gap
- The screenshot of 127.0.0.1:5000 shows features this repository does not contain (a "Dark" toggle, a different dashboard hero, "Records Clear" in the sidebar). Changes here apply to this repository's templates only.

## From CHANGELOG_STEP32_V54_ERRORS_POS_AGENT.md

# Step 32 (v54): error codes, POS checkout API, AI agent tool layer (backend only)

No template or static file changed (freeze test passes).

## 1. Error codes
- `pharmacy/lib.py`: `ERROR_CODES` (medicine_add E-102, medicine_edit E-103, sale_save E-201, user_delete E-301,
  password_reset E-401, reset_code E-402, api_checkout E-501, agent E-601).
- `flash_unexpected(message, code=None)`: the user sees "... Error E-102. Please try again. ... check the log."
  The log line carries the same code.
- Applied to: add medicine (E-102), POS checkout API (E-501).
- `audit_as(...)`: audit rows for API calls (no browser session).

## 2. Medicine columns: NOT added (already exist)
- `barcode` exists, UNIQUE index `uq_medicines_barcode` (from ensure_schema).
- `strength` exists.
- `dosage_form` exists and is the same as the requested `form`.
- `rack_location` exists and is the same as the requested `shelf_location`.
Adding duplicate columns would split the data. Renaming needs a decision (templates use the current names).

## 3. POS checkout API
- `POST /api/pos/checkout` (Bearer token, Admin or Pharmacist token linked to a user).
- Body: `items` (barcode or medicine_id, quantity), `payment_method`, `customer_id`, `discount`, `discount_type`,
  `paid`, `prescription_id`.
- Returns 201 `{sale_id, total, paid, balance}`; 400 for a problem the cashier fixes; 409 for the same bill sent
  again within 10 seconds; 403 when the token has no user; 500 with Error E-501.
- Same rules as the counter (`services/sales.py`): stock lock, FIFO batches, prescription rule, discount caps,
  udhaar needs a customer, double-submit guard.
- `api_tokens.user_id` (new, legacy ADD COLUMN in ensure_schema). `scripts/create_api_token.py "Label" Admin|Pharmacist [username]`.

## 4. AI agent tool layer (`pharmacy/services/agent_tools.py`, migration 007)
- READ (SELECT only): find_medicine, low_stock, expiring, today_summary, find_customer.
- WRITE (whitelist: set_shelf_location, add_customer), two steps:
  - propose(): stores the change, returns a token `agt_...` valid 5 minutes. Only its SHA-256 is stored.
    A new proposal cancels the user's older pending one.
  - confirm(): same user only, single use, not expired. Done mark and change in one transaction.
- No route yet: the chatbot/agent will call these functions in a later step.

## Tests
- test_pos_checkout.py: 20 checks. test_agent_tools.py: 27 checks. test_error_codes.py: 6 checks.
- Updated test_coverage_medicines.py expectation for the new add-medicine message (E-102).
- Full suite: 1341 pass, 0 fail (mock DB). Live MySQL NOT run.

## Not in this step
- Agent route/UI, voice, camera barcode scan, mobile app, prescription OCR, online store (see plan).

## From CHANGELOG_STEP4.md

# MediGen AI Pro - Step 4 (login and user security)

## What changed
- **Login lock now in the database** (`login_attempts` table, created automatically on start).
  - Before: the lock was in memory, so a restart or a second worker reset it.
  - Now: 5 wrong passwords lock the username + IP for 5 minutes, even after a restart.
  - The table stores a SHA-256 hash of IP + username, not the raw values.
  - A successful login clears the counter. An expired lock is ignored and reset.
- **Same timing for unknown usernames.** Before, a wrong username answered faster than a wrong password, so an attacker could guess which usernames exist. Now the server always runs one bcrypt check.
- **Locked login is audited** (`login.locked`).
- **Add user checks:**
  - Username: 3 to 40 letters, numbers, dot or underscore.
  - Full name: 2 to 80 characters.
  - Role must be a real role id (checked in the database).
- **Access time checks:** start and end must be HH:MM (24 hour), e.g. 20:00 to 06:00.

## Pharmacy benefit
- A staff member who forgets the password cannot unlock the account by restarting the computer.
- Someone trying random usernames cannot tell which staff names exist.
- Wrong role or time values are caught before they are saved.

## Tests
- Mock suite: 396 pass, 2 fail (the 2 old profile tests, unchanged).
- `tests/test_auth_step4.py` (new, 20 checks): lock key hashing, lock persists in the table, lock expiry, counter reset on success, timing check, user input checks, access time checks.
- `tests/test_security.py` updated: its mock now stores the lock like the database does, and the add-user test uses a valid name.
- Not run here: the live MySQL test (`--live`). Run it on your scratch database before going live.

## Files to put in the project
- Replace: `app.py`, `pharmacy/core.py`, `pharmacy/routes/auth.py`, `pharmacy/routes/users.py`, `tests/test_security.py`.
- New: `tests/test_auth_step4.py`.
- Everything else stays the same.

## Not done in Step 4 (moved to later steps)
- One place for the role matrix (Step 4b or Step 5). Roles are still written in each route.
- Logout by POST only (Step 10).
- Password change and profile checks (Step 10).

## From CHANGELOG_STEP5.md

# MediGen AI Pro - Step 5 (business features)

## What changed
- **Daily Closing** at `/daily-closing` (Admin, Pharmacist).
  - Pick any date (default today; a bad date shows today).
  - Shows: number of bills, units sold, sales total, new customer dues created that day.
  - Money received by Cash, Card, Online (sale-time payments plus customer dues payments on that day).
  - Refunds given that day, and the net (received minus refunds).
  - Print button for the end-of-day paper.
- **Customer Dues** at `/customer-dues` (Admin, Pharmacist).
  - Customers who still owe money, biggest debt first, with total due and oldest sale date.
  - WhatsApp button opens WhatsApp with a Roman Urdu / English reminder filled in (first name, shop name, amount). The staff member presses Send.
  - Pakistani mobile numbers are converted automatically: 0300-1234567, +92 300 1234567, 3001234567 all become 923001234567.
  - Customers without a valid mobile show "No valid mobile number" instead of a broken button.
  - Walk-in sales (no customer) are not listed, because there is no one to remind.
- Nav: two new links under Transactions ("Daily Closing", "Customer Dues") for Admin and Pharmacist.
- Cashier cannot open either page.

## Files
- `pharmacy/business_rules.py` (new): phone number rule, reminder text, WhatsApp link. No database, easy to test.
- `pharmacy/repos/business.py` (new): SQL for the closing totals and the dues list.
- `pharmacy/routes/business.py` (new): the two pages.
- `pharmacy/routes/__init__.py`: registers the new routes.
- `templates/closing.html` (new), `templates/customer_dues.html` (new).
- `templates/base.html`: two nav links.
- `tests/test_business_step5.py` (new, 27 checks).

## Tests
- Mock suite: 423 pass, 2 fail (the 2 old profile tests, unchanged).
- URL map: 66 routes. Two new (`/daily-closing`, `/customer-dues`). None removed.

## Pharmacy benefit
- End of day: the cashier and owner see the same total without adding paper bills by hand.
- Customer dues: one click sends a polite reminder; no need to write each message or copy numbers.

## Not done in Step 5 (planned for later)
- Expiry return claim (list of expiring stock to send back to the supplier): needs a new table, so it is its own step.
- Barcode field on medicines and scanning in the sale screen: needs a database column and JavaScript; next step.
- GST per item: the current tax is one rate for the whole bill; per-item GST changes the sales and invoice logic, so it needs a decision first.
- Refunds are not split by payment method (the current data does not record how a refund was paid).

## Files to put in the project
- Replace: `templates/base.html`, `pharmacy/routes/__init__.py`.
- New: `pharmacy/business_rules.py`, `pharmacy/repos/business.py`, `pharmacy/routes/business.py`, `templates/closing.html`, `templates/customer_dues.html`, `tests/test_business_step5.py`.
- Everything else stays the same.

## From CHANGELOG_STEP6.md

# MediGen AI Pro - Step 6 (English / Roman Urdu), part 1

## What changed
- **Language switch** in the top bar: button "Roman Urdu" (or "English" when Roman Urdu is on).
  - English is the default. Roman Urdu is shown only when the user chooses it.
  - The choice is saved in the user's session, so it stays while they work.
- **Sidebar labels** come from one file: `pharmacy/i18n.py` (English and Roman Urdu for each label).
  - Examples: Medicines / Dawaiyan, New Sale / Nayi Sale, Daily Closing / Roz ka Hisaab, Customer Dues / Udhaar.
  - Adding or changing a label means editing this one file, not every template.
- `/language` route (POST only, CSRF protected). It refuses unknown languages and only redirects back to this site.

## Tests
- Full mock suite: 473 pass, 2 fail (the 2 old profile tests, unchanged).
- `tests/test_i18n_step6.py` (new, 18 checks): every label has both languages, fallback to English, language
  values cleaned, switch button shows and carries the token, choice saved, sidebar changes, unknown value refused,
  no redirect to another website, switch without token refused.
- URL map: 67 routes (1 new: `/language`).

## Pharmacy benefit
- Staff who are more comfortable in Roman Urdu can use the menu in it; English stays for everyone else.

## Not done yet (Step 6 part 2)
- Page titles, headings, buttons and table headers on each page (only the sidebar is translated now).
- Flash messages (the small messages after saving) are still English.
- The greeting ("Good morning") is still English.
- Customers page: hide medical history from Cashier; Medicines page: hide cost price from Cashier (open audit items).

## Files to put in the project
- Replace: `templates/base.html`, `pharmacy/lib.py`, `pharmacy/routes/__init__.py`.
- New: `pharmacy/i18n.py`, `pharmacy/routes/language.py`, `tests/test_i18n_step6.py`, `CHANGELOG_STEP6.md`.
- Everything else stays the same.

## From CHANGELOG_STEP6B_LABELS.md

# MediGen AI Pro - Step 6 part 2 (first part): Roman Urdu page labels

## Done
- Greeting ("Good morning" / "Good afternoon" / "Good evening" and "Welcome back") now follows the language switch.
- Dashboard: welcome text, stat cards, chart and alert headings, quick action labels.
- Medicines page: title, subtitle, Add Medicine button, search placeholder, table headers.
- Customers page: title, subtitle, stat labels, Add New Customer button, search placeholder, table headers.
- `pharmacy/i18n.py`: about 60 new English / Roman Urdu pairs.

## Not done yet (next part)
- Flash messages (small messages after saving) are still English.
- Other pages: Sales, New Sale, Purchases, Prescriptions, Batches, Reports, Users, Settings, Profile, modal dialogs and form fields.

## Already done before this step
- Cashier does not see cost price (Medicines page and CSV) or medical history (Customers page).

## Test
- `tests/test_step6b_labels.py` (9 checks). Full suite: 508 passed, 0 failed.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5. Click the "Roman Urdu" button in the top bar to switch.

## From CHANGELOG_STEP6C_SALES_FLASH.md

# MediGen AI Pro - Step 6 part 2 (second part): Sales, New Sale and flash messages

## Done
- Sales Records page: title, subtitle, stat labels, Create New Sale, Search button, table headers.
- Create New Sale page: title, subtitle, customer and payment labels, barcode placeholder, table headers, Add Another Item, discount, payment received, Complete Sale, Add New Customer dialog title.
- Flash messages (small messages after saving or errors): 69 fixed messages now show in Roman Urdu when Roman Urdu is selected (`FLASH_UR` in `pharmacy/i18n.py`).
- Messages that include a number or a name (for example "Medicine 5 deleted", "Insufficient stock for ...") stay in English. They can be added one by one later.

## Not done yet
- Purchases, Prescriptions, Batches, Categories, Suppliers, Reports, Users, Settings, Profile, Daily Closing, Customer Dues pages.
- Modal dialogs and form fields on those pages.
- Flash messages with numbers or names.

## Test
- `tests/test_step6b_labels.py` (14 checks). Full suite: 513 passed, 0 failed.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5. Use the "Roman Urdu" button in the top bar.

## From CHANGELOG_STEP6D_REMOVE_URDU_UI.md

# MediGen AI Pro - Step 6D: Roman Urdu UI removed

## Why
The client asked to remove the Roman Urdu page language. The whole UI is English again. The greeting stays "Good morning / afternoon / evening".

## Removed
- The "Roman Urdu" / "English" button in the top bar, and its `/language` route (`pharmacy/routes/language.py`).
- `pharmacy/i18n.py` (labels table and the flash message list).
- The language helpers in `pharmacy/lib.py` (`t()`, `tf()` and `inject_language`).
- Page labels added in Step 6 part 2 on Dashboard, Medicines, Customers, Sales and New Sale. These pages are back to the English text.
- Tests: `tests/test_i18n_step6.py`, `tests/test_step6b_labels.py`.

## Kept
- Chatbot still answers in English or Roman Urdu depending on the question (AI Assistant page).
- The Language field on the user profile (stored as text, not used for page labels).

## Test
- Full suite: 481 passed, 0 failed.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5.

## From CHANGELOG_STEP6E_SIDEBAR_MENU.md

# MediGen AI Pro - Step 6E: Sidebar Menu slide and red Logout

## Changed
- Sidebar first view: Dashboard, a "Menu" button, and a red Logout button.
- "Menu" slides in the full list from Medicines down to My Profile (Medicines, Batches & Expiry, Categories, Customers, Suppliers, Transactions, Admin, AI Assistant, Settings, My Profile).
- Small back arrow at the top of the Menu panel slides back to the first view.
- Logout is a solid red button under the Menu button (it was hard to see before, because the CSS targeted a link, not the button).
- Role rules are unchanged: Suppliers, Purchases, Prescriptions, Admin section and Settings still show only for the roles that could see them before.

## Files
- templates/base.html (sidebar markup and a small script for the Menu / back buttons), pages.css v27.

## Test
- Full suite: 481 passed, 0 failed.
- Screenshot check in the sandbox: root view and Menu view both render. Bootstrap icons do not load in the sandbox, so icons may show as blank boxes there. They load on your PC.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5.

## From CHANGELOG_STEP6F_LOGOUT_PINNED.md

# MediGen AI Pro - Step 6F: Logout pinned at the bottom of the sidebar

## Changed
- Logout (red button) is now fixed at the bottom of the sidebar on every page. It no longer scrolls away.
- The sidebar has three parts: header and user card at the top, menu in the middle (scrolls inside the sidebar), and Logout at the bottom.
- "Menu" still slides in the full list (Medicines down to My Profile), with the small back arrow at the top to slide back.

## Files
- templates/base.html: Logout form moved to a `sidebar-foot` block after the menu. Stylesheet bumped to pages.css v28.
- static/css/pages.css: pinned footer, scrolling menu panes, red Logout button.

## Test
- Full suite: 481 passed, 0 failed.
- Sandbox screenshots: Dashboard view and Menu view both show Logout at the bottom.

## Install
1. Replace the whole project folder (all files, including templates/base.html and static/css/pages.css).
2. `python app.py`, then Ctrl+F5 in the browser.

## From CHANGELOG_STEP6G_BACK_ARROW.md

# MediGen AI Pro - Step 6G: Flat sidebar and back arrow on every page

## Changed
- Sidebar: no "Menu" button. All pages are in one list (Dashboard, Medicines, Batches & Expiry, Categories, Customers, Suppliers, Sales, New Sale, Purchases, Prescriptions, Daily Closing, Customer Dues, Reports, Users, Records Clear, AI Assistant, Settings, My Profile). The list scrolls if needed.
- Red Logout button stays pinned at the bottom of the sidebar.
- Back arrow (round button, top left of the page header) on every page. It goes to the previous page, or to the Dashboard if there is no previous page.

## Test
- Full suite: 481 passed, 0 failed.
- Sandbox screenshot: flat list, Logout at the bottom, back button in the header. Icons are blank only in the sandbox (no internet for Bootstrap Icons).

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.

## From CHANGELOG_STEP6H_LOGOUT_BACK.md

# MediGen AI Pro - Step 6H: Logout in the menu, back arrow fix

## Changed
- Logout (red button) is now the last item of the sidebar list, under My Profile. It is no longer pinned at the bottom.
- Back arrow: hidden on the Dashboard. Shown on every other page.
- Back arrow now uses its own page stack in the browser (sessionStorage), not the browser history. Login and logout reset the stack, so the arrow no longer lands on a blank or login page after logging in again.

## Test
- Full suite: 481 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5. Log out once and log in again to clear the old page stack.

## From CHANGELOG_STEP6I_BACK_POPUPS.md

# MediGen AI Pro - Step 6I: Back arrows in popups, no back on Login/Dashboard, login redirect

## Changed
- Back arrow is hidden on the Dashboard and on the Login / Forgot password pages. It shows on every other page.
- Every popup (Add Medicine, Edit Medicine, Adjust Stock, Add Category, Add Customer, Receive payment, etc.) has a back arrow in its header. It closes the popup and keeps you on the same page.
- A logged-in user who opens /login (or /) is sent to the Dashboard. The login page no longer shows inside the app layout after login.

## Files
- templates/base.html: back arrow condition, popup back arrows (script), stylesheet v33.
- static/css/pages.css: popup back arrow style.
- pharmacy/routes/auth.py: logged-in GET /login redirects to the Dashboard.
- tests/test_auth_step4.py: test helper gets the CSRF token from the Dashboard when already logged in.

## Test
- Full suite: 481 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.

## From CHANGELOG_STEP6J_POPUP_BACK.md

# MediGen AI Pro - Step 6J: Back arrow in every popup (fixed selector)

## Changed
- Popups (Add New Medicine and every other popup) now show a back arrow in the header, to the left of the title. It closes the popup and keeps you on the same page.
- The arrow is added automatically to all popups, including popups on pages added later. No page needs extra code.
- Popup headers that use the `modal-header-custom` class are now included (the previous version missed them).

## Test
- Full suite: 481 passed, 0 failed.
- Browser check: all 5 popups on the Medicines page get a back arrow.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.

## From CHANGELOG_STEP7.md

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

## From CHANGELOG_STEP8.md

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

## From CHANGELOG_STEP9.md

# MediGen AI Pro - Step 9 (Chatbot with optional Claude API, offline first)

## What changed
- The chatbot still works fully offline. It answers stock, sales, expiry, dues and customer questions from the database as before.
- Only when the offline engine says "I did not understand", AND a key is set in `.env`, the question is sent to Claude.
  - Reply is shown with a note: *AI answer. Please verify with a licensed pharmacist before any clinical decision.*
  - If Claude is down, the key is wrong, or the internet is off, the normal offline message is shown. Nothing breaks.
- **Privacy:** only the typed question (max 300 characters) and a fixed pharmacy prompt are sent.
  No customer, patient, sales, stock or user data is sent. The key is never shown in the browser, in logs or in chat history.
- Settings added in `.env` (all optional):
  - `CLAUDE_API_KEY` (empty = offline only)
  - `CLAUDE_MODEL` (default `claude-haiku-5-5`)
  - `CLAUDE_TIMEOUT` (default 15 seconds)
  - `AI_ENABLED` (default 1; set 0 to switch AI off without removing the key)

## Files
- New: `pharmacy/ai_client.py` (Claude call, uses only Python standard library, no new package)
- Changed: `pharmacy/lib.py`, `pharmacy/core.py`, `chatbot_engine.py`, `config.py`
- New test: `tests/test_ai_step9.py` (23 checks, mock network, no real API call)
- Reference only: `.env.example` (do not overwrite your real `.env`)

## Tests
- Full mock suite: 496 pass, 2 fail (the 2 old profile tests, unchanged).
- Step 9 checks cover: AI off without key, no network when off, correct endpoint and headers,
  only the question is sent, no shop data in request, key not in body or chat response,
  timeouts and HTTP 401 handled, Claude used only for unknown questions, offline message when Claude is down.
- Not tested against the real Anthropic service from this environment (no internet access here).

## Pharmacy benefit
- Staff can ask in plain English or Roman Urdu. Questions the shop software cannot read still get a helpful answer
  when internet is available. Shop data stays on the shop computer.

## Your steps
1. Replace the changed files listed above. Put the new files in place.
2. Open your real `.env` and add the lines from `.env.example` (only the 4 AI lines). Add your key after `CLAUDE_API_KEY=`.
   Do not paste the key into any chat, screenshot or file in the project.
3. Restart `python app.py`.
4. Type an unknown question, for example "kya aap bata sakte hain xyz". Expect the AI note.
   Leave `CLAUDE_API_KEY` empty to confirm the offline message.

## From CHANGELOG_STEP9B_OPENAI.md

# MediGen AI Pro - Step 9b (OpenAI option for the chatbot)

## What changed
- The chatbot can now use **OpenAI (ChatGPT API)** as well as Claude. Choose one in `.env`:
  - `AI_PROVIDER=openai` (or `anthropic`, the default)
  - `OPENAI_API_KEY=` your key from the OpenAI platform
  - `OPENAI_MODEL=gpt-5-mini` (change it if you want another model)
- Same rules as before: offline first; AI only for questions the offline engine does not understand;
  only the question and a fixed pharmacy prompt are sent; no shop, customer or patient data; key never shown or logged.
- If the key is empty or `AI_PROVIDER` is not set, the chatbot stays offline.

## Files
- Replace: `config.py`, `pharmacy/ai_client.py`, `pharmacy/lib.py`, `tests/test_ai_step9.py`, `.env.example` (reference only)
- New: `tests/test_ai_openai.py` (15 checks), `CHANGELOG_STEP9B_OPENAI.md`

## Tests
- Full mock suite: 522 pass, 2 fail (the 2 old profile tests, unchanged).

## Your steps
1. Replace the files above. Do not overwrite your real `.env`.
2. In `.env`, set:
   ```
   AI_PROVIDER=openai
   OPENAI_API_KEY=your_new_key_here
   OPENAI_MODEL=gpt-5-mini
   ```
3. Restart `python app.py`, then ask an unknown question in the chatbot.

## Important
- The key you shared in the chat has been exposed. Delete it on the OpenAI platform and create a new one.
- Never paste the key into chat, screenshots or project files.

## From CHANGELOG_STEP9C_GEMINI.md

# MediGen AI Pro - Step 9c (Gemini option for the chatbot)

## What changed
- The chatbot can use **Google Gemini** (model `gemini-2.5-flash` by default). Set in `.env`:
  - `AI_PROVIDER=gemini`
  - `GEMINI_API_KEY=` your new key from Google AI Studio
  - `GEMINI_MODEL=gemini-2.5-flash`
- Same rules as before: offline first; AI only for questions the offline engine cannot read; only the question and a fixed pharmacy prompt are sent; no shop, customer or patient data; key never shown or logged.
- New test script: `scripts/test_gemini.py` checks your key directly. Run `python scripts/test_gemini.py` from the project folder.

## Files
- Replace: `config.py`, `pharmacy/ai_client.py`, `.env.example` (reference only)
- New: `scripts/test_gemini.py`, `tests/test_ai_gemini.py` (12 checks), `CHANGELOG_STEP9C_GEMINI.md`

## Tests
- Full mock suite: 536 pass, 0 fail.
- Not yet checked against the live Gemini service: run `scripts/test_gemini.py` with your real key to confirm.

## Your steps
1. Create a new key in Google AI Studio. Do not paste it into chat or screenshots.
2. In `.env` set:
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_new_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
3. Run `python scripts/test_gemini.py`. You should see the MediGen intro. If not, the message shows the reason.
4. Restart `python app.py`.

## Note
- The terminal earlier showed "Claude API returned HTTP 401" while the Claude key was empty. That came from an old running server. Restarting fixes it.

## From CHANGELOG_STEP9D_GEMINI_FALLBACK.md

# MediGen AI Pro - Step 9d (Gemini fallback models)

## What changed
- If the main Gemini model is busy (HTTP 503) or over its limit (HTTP 429), the app now tries the next model automatically.
- Default order: `GEMINI_MODEL`, then `gemini-2.5-flash-lite`, then `gemini-2.5-flash`.
- Errors such as a wrong key (400) or no permission (403) are not retried, because another model will not fix them.
- Optional `.env` line (default already set):
  `GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite,gemini-2.5-flash`

## Files
- Replace: `config.py`, `pharmacy/ai_client.py`, `tests/test_ai_gemini.py`, `.env.example` (reference only)

## Tests
- Full mock suite: 538 pass, 0 fail.
- New checks: busy model falls back to the next model; bad key is not retried.

## Your steps
1. Replace the files above. Do not overwrite your real `.env`.
2. Restart `python app.py`, then run `python scripts/test_gemini.py`.


## Earlier CHANGELOG.md

# MediGen AI Pro - CHANGELOG

## v100.00 - 2026-11-20
- Security hardening (CSP header) + the owner screenshot fixes SS1-SS4 (BUGFIX_LOG.md).
- Form & card system: one both-mode rule set for every input/select/modal.
- Remember-me: desktop window data folder pinned; dashboard cash card shows the drawer opening.
- Bootstrap/Chart.js vendor files bundled - the app now runs fully offline.
- Mixed medicine+drip sale (B1) and expired-batch block (B3) verified live in a browser. (major versions)

## v88.00

One version source: `Config.APP_VERSION = '88.00'` in `config.py`. The About page,

## v89.00

Version: `Config.APP_VERSION = '89.00'` (one source, as always).

## v92.00

Fix release for three complaints from the owner's own screenshots:

## v93.00

## Frontend: "Signature" professional look (owner-approved demo, then full rollout)

## v94.00

Owner ki final pasand par banaya gaya: Ivory + Bronze sidebar, halki welcome

## v95.00

Owner ke bheje hue "MediGen Nexus — Premium Light UI Concept" ke 62 design

## v96.00

Theme file: v96-theme.css (Nexus look waisa hi — koi rang tabdeel nahi).

## v97.00

Theme file: v97-theme.css (Nexus look waisa hi). v96.00 ki tamam features barqarar

## v98.00

Theme file: v98-theme.css (Nexus look waisa hi). v97 ki tamam features barqarar.

## v99.00 - Stage 1 (Master Prompt v00): audit + cleanup. Gemini-only AI, license system removed,
branches/owner summary archived, one start file (START_MEDIGEN.bat). Details: CHANGES.md + CLEANUP_LOG.md.
