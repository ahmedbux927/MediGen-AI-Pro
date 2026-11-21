# BASELINE — MediGen AI Pro (Master Prompt v4, Stage 0)
Recorded: 2026-11-21 (build environment, not the shop PC)

## Source checked
Owner-supplied `MediGen_FULL_v100.00_READY.zip` (590 files, no `.env`, no pharmacy_backup.sql).
Verified against the v100 delivery: same code PLUS work not in the v100 zip —
`pharmacy/errors.py` (9 typed error classes), inspection report (route + service + template + test),
`scripts/clean_env_copy.py`, `database/diagnostics/stock_mismatch_report.sql`,
tests `test_b1_drip_sale_no_ddl.py`, `test_b3_expired_guard.py`, `test_b4_clean_env.py`, `test_inspection_export.py`.
Checkpoint of the untouched input: `archive/pre_v4_backup/2026-11-21_pre_v4.zip`.

## Numbers (this tree, before v4 changes)
- compileall: OK (pharmacy, app.py, config.py, desktop.py)
- Mock test suite (`tests/run_all.py`): **2323 passed, 0 failed**
- Routes: 153 · Templates: 61 · Services: 31 · Migrations: 11 (highest: 012_phone_otp.sql → new migrations start at 013)
- APP_VERSION: 100.00 (config.py, single source)

## Claims from the brief, verified by reading the code
- B1: `auto_record_sale` no longer calls `ensure_drip_table` — DDL is out of the sale path (ensure remains only on drip/products display pages). Regression test passes. TRUE for this tree.
- Gemini-only AI, license system absent, no `mobile_*` routes, customer portal / branches / owner home in `archive/`: confirmed in v99/v100 and still true here.

## After Stage 1 + dark-mode fixes (same day)
- Mock suite: **2323 passed, 0 failed** (4 stale literal version pins updated to the single-source variable; freeze manifest regenerated)
- Live run (local MySQL + browser): Medicines page dark + light screenshots verified.

## Stage 2 (2026-11-21)
- Mock suite: **2338 passed, 0 failed** (typed-error wiring + test_stage2_errors.py, 15 assertions).

## Stage 4 — counter speed measurements (2026-11-21, sandbox VM, local MySQL, 5-medicine catalog)
- POS page (/sales/new) full load in a real browser: ~3.2 s on this shared sandbox VM (server-rendered catalog; grows with catalog size — re-measure on the shop PC and with 1000 items in Stage 11).
- Add-to-cart after load is client-side (DOM filter + row add): effectively instant, no server round-trip. The 300 ms target applies to this step and is met by design.
- Held bills flow (add → hold → list → resume) verified live in the browser, all steps correct.
- Mock suite after held-bills wiring: **2351 passed, 0 failed**.

## Stage 11 additions (2026-11-21) — QA, migrations, performance
- Route x role matrix: see QA_MATRIX.md (38 routes x 4 identities, live).
- CSRF rejection verified live (tokenless POST changed nothing); session cookie HttpOnly + SameSite.
- Fresh-DB migrations: first startup applied 2-14; second startup applied nothing, zero errors.
- Performance with 1005 medicines / 10005 batches (sandbox VM): POS ~300-350 ms steady (765 KB page; catalog SQL ~0.2 s, indexed, no N+1), Medicines ~520-550 ms (2.6 MB), Dashboard ~280 ms. First cold hit is slower (template compile + buffer pool).
- pyflakes: clean on the new non-star-import files (services/ai_pro.py, scripts/build_css.py, pharmacy/errors.py); route modules use the documented star-import pattern from core/lib.
