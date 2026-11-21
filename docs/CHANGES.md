# CHANGES — Master Prompt v4

## 2026-11-21 — v101.03: Canva icon + user-delete fix + full check (owner's wrap-up order)
- ICON: generated with Canva (media MAHbhmT2wBc) — navy rounded square, white cross, teal pulse, leaf. The black surround was cropped to a full-bleed navy master (corners verified navy), then derived: assets/medigen.ico (7 sizes) + medigen_256 + medigen_master, static/logo.png, favicon, PWA icons, Android mipmaps (all 5 densities). One stray Canva job was lost to a truncated job-id and regenerated once, saving the response to a file.
- USER DELETE (owner: a user would not delete): user_history.py gained fk_references (KEY_COLUMN_USAGE), all_references (user_id scan + named FK columns like counted_by/created_by), placeholder_user ('Deleted user', inactive, random bcrypt), reassign_references. delete_user: placeholder protected, last-active-Admin guard, force=1 path = reassign → delete; default stays deactivate with a clearer message. Users page: delete is now a modal with the permanent tick. Old behavior pins updated (test_user_delete_rules, test_stage9_settings_users); new test_v101_user_delete.py includes a fake-cursor functional test of the scan + reassign.
- FULL CHECK: no bare/silent excepts; only routes/__init__ and errors.py lack @guarded (by design); compileall clean; dark-mode inline-style audit — products_edit Back button inline white style removed (now the themed .pe-btn); medicines/products white bulk buttons and the rx_scan amber alert verified intentional/readable in both modes; font sizes sane (13–16px body). Freeze regenerated.
- Package is LEAN per the owner's "only new" instruction: Server + APK (vCode 104, new icon) + MediGen_Logo.png + INSTALL.txt + STEP_BY_STEP_GUIDE.md — no project docs. Suite **2509 passed, 0 failed**.

## 2026-11-21 — v101.02: Windows app build (owner asked for the Windows application)
- REAL BUG fixed for the exe build: Settings backup/restore subprocess used [sys.executable, script], which inside a PyInstaller exe relaunches the app. `desktop.py` gained a `--script` mode (runpy) and `pharmacy/routes/settings.py` a frozen-aware `_script_cmd` used by both routes.
- `build_exe.bat` now also copies `scripts/` next to the exe (without it, Backup now could never work in the exe).
- NEW `MAKE_WINDOWS_APP.bat`: one double-click — build_exe.bat, then Inno Setup compile when ISCC is found (PATH or the standard install folders), with a clear message otherwise.
- `installer/README.md` rewritten: the old text described a source-copy installer that no longer exists; it now matches MediGen.iss (exe installer, per-user, .env protection, portable MySQL option, SmartScreen note).
- Version 101.02 everywhere (installer AppVersion, Android versionCode 103); APK rebuilt + verified. Tests: test_v101_windows_app.py (9); suite 2502 passed, 0 failed. The exe/Setup compile itself can only run on a Windows PC — not run here, stated plainly.

## 2026-11-21 — v101.01: system theme
- `templates/base.html`: theme init now defaults to System (prefers-color-scheme), writes data-theme-mode; the toggle cycles System → Light → Dark and a live OS change re-applies in System mode. Legacy mgTheme values are honoured as manual modes.
- `static/js/login.js`: login page starts from the saved mode or the system setting; its Light/Dark buttons save the shared mode.
- Version 101.01 in config/tests/Android (versionCode 102); installer/MediGen.iss AppVersion 101.01. APK rebuilt and verified.
- Verified: tests/test_v101_system_theme.py (6) + full suite 2492/0; browser check with emulated OS dark/light (fresh profile follows the OS, toggle cycles, live OS switch updates). Note: the sandbox MySQL test stack was wiped by a VM replacement, so this client-side change was proven in a browser harness built from the real template scripts, not against the full server.

## 2026-11-21 — Stage 12: labels, version 101.00, final package
- Barcode labels: `pharmacy/services/labels_pdf.py` (Code 128 via reportlab), routes GET /products/labels + POST /products/labels/print, `templates/product_labels.html`, Labels link on the Medicines page. Items without a barcode are explained, not silently skipped. Live-verified (real PDF out).
- Version: APP_VERSION 100.00 → 101.00 (config, tests, AndroidManifest, app/build.gradle; APK versionCode 101).
- README.md rewritten in Roman Urdu for v101; CHANGELOG.md v101.00 entry; `OPEN_DECISIONS.md` and `SHOP_TEST_CHECKLIST.md` added at project root.
- APK rebuilt with Stage 10 sources; signature verified; same key as v100 so it updates in place.
- `tests/test_stage12_labels.py` added (5). Final suite: 2486 passed, 0 failed. Package: MediGen_FULL_v101.00_READY.zip.

## 2026-11-21 — Stage 11: QA matrix, security and performance evidence
- `QA_MATRIX.md` (new, project root): live route × role results for 38 routes and 4 identities, the security checks run (CSRF rejection proven in the database, cookie flags, upload caps), the migration double-run result, and the performance table.
- `BASELINE.md`: Stage 11 measurements appended. No application code changed in this stage.
- `tests/test_stage11_qa.py` added (12 assertions). Suite: 2481 passed, 0 failed.

## 2026-11-21 — Stage 10: Android companion hardened
- `android/app/src/com/medigen/aipro/ServerAddress.java` (new): LAN-only address validation; `android/tests/ServerAddressTest.java` (new, 19 cases, passing).
- `MainActivity.java`: uses ServerAddress, error line on the setup screen, "Server not reachable" message, camera permission bridge for web scanning, cookie accept + flush.
- `AndroidManifest.xml`: CAMERA permission + optional camera feature.
- Gradle project added: settings.gradle, build.gradle (AGP 8.5.2), app/build.gradle (namespace/SDK/sourceSets), gradle wrapper properties (8.7).
- `android/BUILD_APK.md` + `android/TEST_CHECKLIST.md` (device items NOT RUN BY AGENT). `tests/test_stage10_android.py` added (12). Suite: 2469 passed, 0 failed.

## 2026-11-21 — Stage 9: settings reset + user editing
- `pharmacy/routes/settings.py`: POST /settings/reset restores one group (shop/money) to SETTING_DEFAULTS, audited; Reset buttons with confirmation added to the Shop and Money panes.
- `pharmacy/routes/users.py`: POST /users/edit/<id> changes full name and role; the only active Admin cannot be demoted; audited. Users page gains an Edit button + modal per user.
- `tests/test_stage9_settings_users.py` added (11 assertions); live round-trips verified on real MySQL. Suite: 2457 passed, 0 failed.

## 2026-11-21 — Stage 8: one design system + double-submit guard
- `scripts/build_css.py` (new) generates `static/css/app.css` from the 14 part stylesheets in cascade order; `templates/base.html` now links app.css + fonts.css only.
- `static/js/submit-guard.js` (new): POST forms disable their submit buttons on submit (double-click cannot duplicate a sale/purchase); loaded from base.html.
- 11 stylesheet-link test pins updated to assert the bundle (same intent: the layer's styles reach app pages); freeze manifest regenerated.
- `tests/test_stage8_design.py` added (21 assertions). Suite: 2446 passed, 0 failed.

## 2026-11-21 — Stage 7: pharmacy features end-to-end check
- No feature code changed: the audit found every Stage 7 feature present and working. Live crawl: 32/32 pages HTTP 200 on real MySQL. Stock-count lifecycle proven live end to end (stock 800 → 799 after Admin approval; partial counts refused at submit by design).
- `tests/test_stage7_features.py` added (31 assertions) so the feature route surface cannot silently shrink. Suite: 2425 passed, 0 failed.

## 2026-11-21 — Stage 6: AI Pro guardrails
- `pharmacy/services/ai_pro.py` (new): RateLimiter (20/min per user), TTLCache (10 min), build_summary_prompt (aggregate numbers only — names/phones can never enter it).
- `pharmacy/routes/chatbot.py`: /chatbot/api enforces the rate limit (429) and caches repeated general answers for 10 minutes; live-data questions are never cached.
- `pharmacy/routes/dashboard.py` + `templates/dashboard.html`: optional Daily AI Summary card — runs only when `ai_daily_summary` setting is on, generated once per day from aggregates, cached in app_settings, failure-silent.
- `pharmacy/routes/settings.py` + `templates/settings.html`: "Daily AI summary" checkbox on the AI pane (saved only from that pane); stale OpenAI/Claude copy corrected.
- `tests/test_stage6_ai_pro.py` added (18 assertions). Suite: 2394 passed, 0 failed.

## 2026-11-21 — Stage 5: import preview / confirm / undo
- `database/migrations/014_import_preview.sql`: import_previews + import_batches tables.
- `pharmacy/routes/products.py`: GET/POST /products/import-preview (upload CSV/XLSX/PDF → plan preview), GET detail, POST confirm (one transaction via apply_plan; created ids tracked through the audit callback; pre-update snapshot of the changeable fields), POST /products/import-batch/<id>/undo (restores updates, deletes import batches, soft-deletes created items; blocked with reason when any created item has sale_items or purchase_items).
- `templates/import_preview.html` + `templates/import_preview_detail.html`: new pages. Medicines toolbar gains "Import with preview".
- `tests/test_stage5_import_preview.py` added (15 assertions). Suite: 2376 passed, 0 failed. Live browser flow verified end to end.

## 2026-11-21 — Stage 4 (part 2): pack selling + print check
- `database/migrations/013_units_per_pack.sql`: `medicines.units_per_pack INT NULL` (units in one pack/strip; NULL = unit sale only). Stock and prices stay per unit — no business-rule change.
- `pharmacy/routes/products.py` + `templates/products_edit.html`: "Units per pack" field, validated 1..10000 or empty, saved in the same UPDATE (audit unchanged).
- `pharmacy/routes/sales.py`: sale page query loads units_per_pack; item options carry `data-pack`.
- `templates/new_sale.html`: `2pk*name` / `2pk*barcode` converts packs to units in both add paths; items without a pack size get a clear English message; keys hint documents it.
- `tests/test_stage4_pack_sale.py` added (10 assertions); test_schedule_field.py pin updated for the widened UPDATE. Suite: 2361 passed, 0 failed.
- Print verified (Playwright print emulation, real sale): thermal 80 mm and A4 invoice — no overflow, receipt shows TOTAL/Paid/QR and no screen-only buttons.

## 2026-11-21 — Stage 4 (part 1): held bills wired
- `pharmacy/routes/sales.py`: POST /sales/hold, GET /sales/held, POST /sales/held/<id>/resume, POST /sales/held/<id>/discard. Resume reuses the sale page's existing prefill path (out-of-stock lines are filtered with a warning, same as prescription prefill). Holding does not reserve stock (service rule, unchanged).
- `templates/new_sale.html`: "Hold bill" button (formaction) + "Held bills" link under Complete Sale.
- `templates/held_bills.html`: new page — open holds with items, customer, note, Resume/Discard.
- `tests/test_stage4_held_bills.py` added (13 assertions). Suite: 2351 passed, 0 failed. Live browser flow verified.

## 2026-11-21 — Stage 2: exception handling wired
- `pharmacy/routes/errors.py`: new `MediGenError` handler — typed errors return their safe `user_message` (flash + back on web, stable JSON + mapped status on /api/), `detail` is logged only.
- `pharmacy/services/sales.py`: `BillError` now subclasses `MediGenError` and `ValueError` (no behaviour change at existing catch sites; uncaught bill errors get the friendly typed response instead of a generic 500).
- `pharmacy/core.py`: the log-setup `except OSError: pass` now prints a warning to stderr (no silent excepts left in pharmacy/ — enforced by test).
- `tests/test_stage2_errors.py` added (15 assertions). Suite: 2338 passed, 0 failed.

## 2026-11-21 — Stage 0, Stage 1, dark-mode fix (base: owner-supplied v100 READY zip)
- BASELINE.md created from the attached zip (verified ahead of the v100 delivery: typed errors module, inspection report, B1/B3/B4 tests already present).
- Hubs reviewed: every menu entry is pharmacy work; nothing archived (CLEANUP_LOG.md).
- HANDOVER_CLOSE_PROJECT.md and PROJECT_AUDIT.md moved to Server/archive/docs/.
- Version single source: new context processor injects `app_version` into all templates; medicines.html no longer hard-codes "Build v87.23"; 4 stale literal pins updated; freeze manifest regenerated.
- Dark mode (owner's shop screenshots): medicine-look components had hard-coded white backgrounds with no dark variants — toolbar card, ghost buttons, filter tabs, the sticky ACTIONS column and pager stayed white in dark mode. Added a dark companion block to v100-theme.css covering .toolbar, .btn-ghost, .filter-tabs, .btn-icon, .med-count, .med-mic, sticky medicines-table last column, .pager, and section-page .pd-tab/.pd-btn.light/.pd-note. Verified live with browser screenshots in both modes.
- Tests: mock suite 2323 passed, 0 failed (same as baseline).
