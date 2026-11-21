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
