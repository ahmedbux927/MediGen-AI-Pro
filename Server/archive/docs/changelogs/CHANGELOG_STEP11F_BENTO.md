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
