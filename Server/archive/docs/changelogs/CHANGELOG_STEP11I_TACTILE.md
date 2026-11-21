# MediGen AI Pro - Step 11I: Hyper-Minimal Tactile 3D Layer

## What changed (vs Ultimate 11H)
- Background is calm: the hairline grid and aurora are removed (`body::before` off). One solid surface.
- Cards have three real elevation levels: rest, hover (lifts 2px) and pressed (sinks).
- Primary buttons are physical keys: a visible lip under the button, the key travels down when pressed.
- Secondary buttons are raised keys with a pressed state.
- Sidebar active item is a pressed key (inset shadow), no gradient.
- Inputs are pressed wells with a soft inner edge.
- Tables have more breathing room; row hover is a soft white wash.
- Bento gap is 20px (16px on small screens).

## Files
- NEW `static/css/tactile.css` (v19), loaded last.
- `templates/base.html`: links `tactile.css?v=19`. All theme files bumped to `?v=19`.
- NEW `tests/test_step11i_tactile.py` (5 checks).

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 592 passed).
