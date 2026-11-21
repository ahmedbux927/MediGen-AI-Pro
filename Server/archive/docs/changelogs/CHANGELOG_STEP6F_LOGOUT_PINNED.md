# MediGen AI Pro - Step 6F: Logout pinned at the bottom of the sidebar

## Changed
- Logout (red button) is now fixed at the bottom of the sidebar on every page. It no longer scrolls away.
- The sidebar has three parts: header and user card at the top, menu in the middle (scrolls inside the sidebar), and Logout at the bottom.
- "Menu" still slides in the full list (Medicines down to My Profile), with the small back arrow at the top to slide back.

## Files
- templates/base.html: Logout form moved to a `sidebar-foot` block after the menu. Stylesheet bumped to pages.css v28.
- static/css/pages.css: pinned footer, scrolling menu panes, red Logout button.

## Test
- Full suite: 481 passed, 0 failed.
- Sandbox screenshots: Dashboard view and Menu view both show Logout at the bottom.

## Install
1. Replace the whole project folder (all files, including templates/base.html and static/css/pages.css).
2. `python app.py`, then Ctrl+F5 in the browser.
