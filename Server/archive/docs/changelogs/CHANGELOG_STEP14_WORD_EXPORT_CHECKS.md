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
