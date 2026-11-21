# Step 31 (v53): professional silver theme and AI assistant panel (FRONTEND change, on purpose)

First intentional frontend change since the freeze. Manifest refreshed with `python tests/test_backend_freeze.py --write`.

## Changes
1. `static/css/pro.css` (new, loaded last in base.html):
   - Silver page background (#d9dfe7 to #cdd5e0), white cards with light border and shadow.
   - Thin sidebar scrollbar.
   - Assistant panel styled like the approved mockup: navy-to-teal header, robot logo, green online dot, round X button, 18px corners.
   - Launcher: pill with a robot badge and "AI Assistant" label.
   - Mobile: panel fills the width, 72% height.
2. `templates/base.html`:
   - Assistant panel (bottom right). X closes it to the launcher. Open or closed state is remembered in this browser (localStorage with try/catch). Default: open on wide screens, closed on phones.
   - Auto-collapse to the launcher after 3 minutes with no activity, in the page and inside the chat iframe. It never collapses while a question is typed. Chat history is kept.
   - `embed-mode` hides the sidebar and top bar when `?embed=1` is used (chat page inside the panel).
3. No backend route, SQL or service changed.

## Tests
- `python tests/run_all.py`: all pass (manifest refreshed).
- Templates parse; frontend tests pass.
- NOT checked in a real browser with the live database.

## Known gap
- The screenshot of 127.0.0.1:5000 shows features this repository does not contain (a "Dark" toggle, a different dashboard hero, "Records Clear" in the sidebar). Changes here apply to this repository's templates only.
