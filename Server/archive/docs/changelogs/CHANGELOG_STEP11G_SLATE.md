# MediGen AI Pro - Step 11G: Soft Slate Neumorphic Enterprise Theme

## Design
- Mid-tone slate surface (`#dde3eb`). Not too light, not too dark.
- Raised neumorphic cards, sidebar and buttons. Pressed (inset) inputs and active nav items.
- Deep slate text, muted teal and slate-blue accents. No neon, no glow.
- Same layout and components as before; only colour, depth and surfaces changed.

## base.html (full file, fixed)
- Clean structure: `<aside class="sidebar">`, `<main class="main-content">`, `<header class="top-bar">`.
- Inline `style=` attributes removed. Top bar uses classes `lang-form` and `lang-btn`.
- All theme CSS is linked, in order: `light.css` -> `bento.css` -> `enterprise.css` -> `slate.css` (last, wins).
- All theme and script files bumped to `?v=17` so browsers load the new CSS.
- `<html lang>` follows the language setting.
- Sidebar links, admin/role rules, mobile menu, data-method POST links and the greeting are unchanged.
- Nav order is unchanged.

## Other
- `static/css/slate.css`: top bar helper classes added.
- `static/css/bento.css`: dead mesh background removed. Bento grid gets its own bottom spacing (does not rely on Bootstrap utilities).
- Tests updated for the new structure (CSS layers instead of inline style block; mesh checks removed). `tests/run_all.py`: 578 passed, 0 failed.

## Install
1. Replace the project folder (or copy `templates/base.html`, `static/css`, `tests`).
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py`.

## Notes
- `spatial.css`, `neu.css` and `style.css` (legacy) are not linked by base.html. Delete `neu.css` if it is still in your folder.
