# MediGen AI Pro - Step 6H: Logout in the menu, back arrow fix

## Changed
- Logout (red button) is now the last item of the sidebar list, under My Profile. It is no longer pinned at the bottom.
- Back arrow: hidden on the Dashboard. Shown on every other page.
- Back arrow now uses its own page stack in the browser (sessionStorage), not the browser history. Login and logout reset the stack, so the arrow no longer lands on a blank or login page after logging in again.

## Test
- Full suite: 481 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5. Log out once and log in again to clear the old page stack.
