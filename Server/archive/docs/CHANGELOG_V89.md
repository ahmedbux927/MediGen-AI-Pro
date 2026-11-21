# MediGen AI Pro v89.00 - what changed

Version: `Config.APP_VERSION = '89.00'` (one source, as always).

## Premium frontend polish
- New `static/css/v89-premium.css`, loaded LAST on every page (and on the login
  page): emerald accent consistency, premium card depth and hover lift, refined
  tables (uppercase micro headers, row hover), rounded inputs with a soft emerald
  focus glow, custom scrollbars, pill badges, modal depth, print-safe.
  The design language, layout and pages are unchanged - this is a polish layer.
- New `static/js/v89-app.js`: toast notifications (`mgToast`), submit buttons get
  a loading state (double clicks are obvious and harmless), and unexpected page
  script errors show one friendly toast - never a stack trace.
- The frontend freeze manifest was regenerated with the test's own `--write`
  option, because the frontend changed on purpose in this version.

## Exception handling, everywhere
- Web: 400, 403, 405, 413 and 429 now get the same friendly treatment as
  404/500 (clear English message, Try again, Back to Dashboard, correct status).
- API: the same errors return the stable JSON shape `{"error": {"code", "message"}}`.
- Server exceptions are logged to `logs/medigen.log` (rotating) as before;
  no stack trace is ever shown to a user.
- Automation: `python scripts/self_check.py` checks the .env keys (names only),
  compiles every Python file, parses every JavaScript file, runs the full test
  suite and writes `logs/self_check_report.txt`.

## AI assistant knows the whole program
- New `docs/PROGRAM_MANUAL.md`: the complete program manual (start/stop, login,
  dashboard, catalog, sales/POS, purchases, prescriptions, reports, backup).
- The ONLINE AI (Gemini -> OpenAI -> Anthropic) now receives a condensed program
  map in its system prompt, so it can answer "how do I..." questions about
  MediGen itself. No shop data is ever sent - only the typed question and the map.
- The built-in offline assistant gained guides for: backup, export, returns,
  barcode, remember me, forgot password, expiry, discount, udhaar, tax,
  printing receipts, settings, starting the server.
- Every AI answer still carries the pharmacist-check note.

## Remember me (password remember)
Already built in and verified in this version: tick **Remember me** at login and
this PC stays signed in for 30 days. The cookie holds a hashed token (never the
password), is HTTP-only, and logging out revokes it at once.

## Checked page by page
Catalog/Products, Medicines, Sales, New Sale (POS), Purchases, Prescriptions,
Reports, Dashboard, Login: all render through the premium layer, and the full
mock suite passes (see README for the count).

## Tests (mock suite, no MySQL)
- v89.00 final: see README.md (updated from the real final run).
- New: `tests/test_v89_premium.py` (40 checks).
- Smoke test (Flask test client): login page, version endpoint shows 89.00,
  API 404 JSON shape, friendly 405 page, chatbot backup/remember guides.

## Still not verified here (no MySQL / no Windows in the build environment)
Live MySQL flows, a real browser (Playwright) run, Windows scripts on a real PC.
Run `python scripts/self_check.py` and `python tests/run_all.py --live` on the
shop PC for those.
