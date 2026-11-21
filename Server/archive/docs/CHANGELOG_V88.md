# MediGen AI Pro v88.00 - what changed

One version source: `Config.APP_VERSION = '88.00'` in `config.py`. The About page,
the startup banner and `GET /api/server/info` all read it. (B5)

## Bugs fixed
- B1: `app.py` now serves with **waitress** by default. The Flask development
  server is only a fallback and prints a clear English warning.
- B2: startup now checks for duplicate live barcodes FIRST (barcode + medicine
  names are logged). The unique index `uq_medicines_barcode` is added only when
  no duplicates exist. Nothing is deleted or merged. Read-only check:
  `database/check_duplicate_barcodes.sql`.
- B3: `pdfplumber` added to `requirements.txt`.
- B5: About page version reads `Config.APP_VERSION` (was hard-coded 1.1.0).
- B8: new money tests (`tests/test_v88_money.py`): 0% tax identity, tax-free
  half-paisa rounding, return restores the same batch, stock never negative
  unless `allow_short`.
- B10: `STOP_MEDIGEN.bat` takes the PID from the LAST netstat column.
- B12: README test counts updated from a real run (see README.md).
- Backup safety (found during v88 testing): a failed backup run could delete an
  earlier good backup made in the same minute. `scripts/backup_db.py` now writes
  to a `.tmp` file and renames only on success.

## Phone app removed
The Android app, Capacitor project, phone-only API routes, WhatsApp OTP reset,
offline phone queue and phone discovery were removed. Full list and the server
contracts that were kept: `REMOVED_PHONE_CODE.md`.

## Enhancements
- E1 Dashboard cards link to filtered lists (low stock, out of stock, expiring
  30/60/90 days, today's sales, reports).
- E2 CSV export for purchases added (sales / profit / stock / expiry / tax
  already existed). All CSV exports use the chosen date range and UTF-8 BOM.
- E3 A4 and 80 mm receipts both show shop name, phone, footer and the same
  totals from the same bill calculation.
- E4 New `static/css/v88-polish.css`: visible focus rings, 44 px controls,
  reduced-motion support. Loaded last; the design language is unchanged.
- E5 New `static/js/v88-utils.js`: `mgDebounce` (250 ms) for search inputs so a
  search is not sent on every keystroke.
- E6 API errors use one JSON shape: `{"error": {"code", "message"}}`.
  The 404/500 pages have a Try again button. No stack traces are shown.
- E7 Lockout message in English, minimum password 8 characters, session expiry,
  HTTP-only cookies and security headers are covered by tests.
- E8 `START_DESKTOP.bat`: one-click start. It starts the server if needed,
  waits until `/api/server/info` answers, then opens the workbench in the
  default browser. The browser was chosen over a native window because it needs
  no extra install, is covered by the tests, and prints receipts correctly.
  `desktop.py` (native window) is still available.
- E9 Deletes stay safe: medicine delete asks for confirmation, is a soft delete
  and is written to the audit log. Saved sale totals are never edited;
  corrections use returns.

## AI
- Fallback order is now real: configured provider first (Gemini by default),
  then the other providers that have a key, in Gemini -> OpenAI -> Anthropic
  order. Tested with mocked HTTP (timeout, 429, 500, invalid key) in
  `tests/test_v88_ai_fallback.py`.
- Every AI answer shown in the web chat carries the pharmacist-check note
  (`ensure_pharmacist_note` in `pharmacy/ai_client.py`).

## Tests (this build, mock suite, no MySQL)
- Before v88 changes: 2391 passed, 0 failed (with pdfplumber installed).
- After v88 changes: see README.md for the final count. Phone-only test files
  were removed with the phone code; five v88 test files were added.

## Not verified in the build environment (no MySQL / no Windows there)
- Live MySQL purchase orders on a disposable schema.
- `reset_password.py` against a real database (its bcrypt hash pattern is
  unit-tested; the database update itself is not).
- A real `mysqldump` backup (the backup logic is tested with a fake mysqldump
  that succeeds, fails, and is missing).
- Windows auto-start scripts and LAN access from another PC.
- A Playwright browser run (needs MySQL). A Flask test-client smoke test was
  run instead: login page, version endpoint, API 404 shape, auth redirect.
