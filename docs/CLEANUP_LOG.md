# CLEANUP_LOG — Master Prompt v4, Stage 1 (2026-11-21)

## 2026-11-21 — Stage 8: CSS consolidated into one bundle (nothing deleted)
- base.html linked 13 app stylesheets; it now links ONE generated bundle, `static/css/app.css`, built by `Server/scripts/build_css.py` from the 14 part files in the exact old cascade order (brand.css's Google Fonts @import hoisted to the top, as CSS requires). The part files REMAIN in static/css/ as the editable sources — the login page and section pages still link v89/v92/v100/medicine-look/inventory directly, so deleting the parts would break them. Rule from now on: edit a part file, run build_css.py, never edit app.css by hand.
- Verified: full suite green; before/after screenshots of dashboard/medicines/POS/settings in both modes are visually identical (pixel noise is the animated aurora phase); computed styles confirm the cascade survived (medicines dark toolbar = #0d1830, the Stage 1 fix; body font = Inter); 390 px overflow = 0 on dashboard/medicines/POS before and after.

## Hub menu review (pharmacy/routes/hubs.py) — every entry KEEP, all pharmacy
- Pharmacy Catalog (Medicines, Syrups, Creams, Drip & Injection, Bandages & Other) — KEEP: the shop's stock sections.
- Inventory (Stock Overview, Batches & Expiry, Expired & Alerts, Cold Chain Log, Stock Count, Categories, Controlled Register) — KEEP: stock, expiry and legal records.
- Sales & Billing (New Sale, Sales History, Cash Drawer, Customers, Customer Dues, Prescriptions, Drug Interactions) — KEEP: counter work and udhaar. Drug Interactions stays as the labelled placeholder (licensed database = OPEN DECISION).
- Purchasing (Suppliers, Purchases, Suggestions, Purchase Drafts, Purchase Forecast, Supplier Returns, Supplier Summary) — KEEP: buying and supplier balances.
- Finance (Expenses, Daily Closing, Profit Margin, Reports, Inspection Report) — KEEP: money and inspection records.
- Admin (Daily Digest, Settings, Users, Activity Log, Data Quality, Records Clear) — KEEP: owner control and audit.
Nothing non-pharmacy found in the hubs; nothing archived from the menus.

## Archived (moved, not deleted)
- `Server/HANDOVER_CLOSE_PROJECT.md` → `Server/archive/docs/` — dev-history handover note.
- `Server/PROJECT_AUDIT.md` → `Server/archive/docs/` — old audit snapshot, superseded by BASELINE.md.
- `REMOVED_PHONE_CODE.md` stays at root: `tests/test_sprint5_release.py` reads it (documented removal record).
- `BUILD_APPS.md` stays until Stage 10 writes `android/BUILD_APK.md`.

## Version single source (B5)
- `templates/medicines.html` showed a hard-coded "Build v87.23". Now shows `{{ app_version }}` via a new context processor in `pharmacy/core.py` (value from Config.APP_VERSION).
- 4 tests pinned the stale literal (test_expenses, test_hubs, test_motion, test_sale_search_v8671); updated to pin the variable instead. Freeze manifest regenerated.

## CSS
- 19 stylesheets remain for now. The dark-mode gaps were in `medicine-look.css` (hard-coded white `.toolbar`, `.btn-ghost`, sticky actions column, pager). Fixed by a dark companion block in `v100-theme.css` (see CHANGES.md). Full merge into one `app.css` is Stage 8 work and must be screenshot-verified page by page — v92-theme.css is load-bearing (proven in v99), so no blind merge.
