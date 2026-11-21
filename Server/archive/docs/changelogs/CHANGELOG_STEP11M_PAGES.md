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
