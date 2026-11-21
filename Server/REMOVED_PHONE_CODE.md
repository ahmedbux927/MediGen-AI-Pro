# v88.00: Phone-only code removed

MediGen AI Pro v88.00 is a workbench program for ONE shop PC (other shop PCs may
open it in a browser on the local network). The Android / phone app is out of
scope, so the phone-only code below was removed. Nothing here deletes shop data.

## Removed files

Top-level package:
- `Android/` (Capacitor 6 phone app) and `ANDROID_STUDIO_AGENT_PROMPT.md`

Server:
- `Server/android/` (native Android WebView wrapper)
- `pharmacy/routes/mobile_admin.py`, `mobile_ai.py`, `mobile_audit.py`,
  `mobile_expenses.py`, `mobile_parties.py`, `mobile_prescriptions.py`,
  `mobile_purchase.py`, `mobile_receipt.py`, `mobile_returns.py`,
  `mobile_rx_manage.py`, `mobile_stock.py` (all `/api/m/*` phone endpoints)
- `pharmacy/routes/phone_otp.py` and `pharmacy/services/otp.py`
  (WhatsApp OTP password reset for phones)
- The `GET /api/sync/snapshot` endpoint in `pharmacy/routes/sync_api.py`
  (offline phone snapshot / phone discovery data)
- `static/js/offline-sale.js` (phone offline bill queue) and its references in
  `templates/new_sale.html` and `static/js/sw.js`
- Docs: `ANDROID_PHONE_SETUP.md`, `CHANGELOG_LAN_ANDROID.md`,
  `docs/MOBILE_APP_GUIDE.md`, `BUILD_APPS_ROMAN_URDU.md`

Tests removed with them (they only tested the files above):
- `tests/test_mobile_*.py` (10 files), `tests/test_phone_sync_v8722.py`,
  `tests/test_android_lan.py`, `tests/test_offline_sale_queue.py`,
  `tests/test_phase1_lock_motion.py`, `tests/test_scanner.py`,
  `tests/test_snapshot_sold_v8738.py`

## Kept on purpose (server contracts the web workbench still uses)

- `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/server/info`
  in `pharmacy/routes/sync_api.py`: token login for API clients and the
  version endpoint. `GET /api/server/info` reads `Config.APP_VERSION`.
- `client_uuid` idempotent POS checkout (`pharmacy/services/pos.py`,
  `tests/test_offline_bill_id.py`): the WEB point-of-sale sends a client_uuid
  so a double submit never creates a second sale. This is a sale-safety
  contract, not phone code.
- The `allow_short` flag in `pharmacy/services/sales.py`: defaults to off for
  every web sale; it exists so the stock rule "never negative unless
  allow_short" can be tested (see `tests/test_v88_money.py`).
- `pharmacy/routes/sync_conflicts.py`: the admin "stock conflicts" page. The
  POS service still records a conflict row when a short sale cannot be covered,
  and the Data Quality page links to it, so the page stays.
- `pharmacy/services/phone_search.py`: despite the name, this searches
  CUSTOMERS by their phone NUMBER for the web POS quick-pick. Not phone-app code.
- Historical `CHANGELOG_*.md` files and `docs/PROJECT_STATUS.md` still mention
  the phone app. They are the project's history and were left unchanged.
