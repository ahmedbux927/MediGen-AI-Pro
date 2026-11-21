# MediGen AI Pro - Step 6I: Back arrows in popups, no back on Login/Dashboard, login redirect

## Changed
- Back arrow is hidden on the Dashboard and on the Login / Forgot password pages. It shows on every other page.
- Every popup (Add Medicine, Edit Medicine, Adjust Stock, Add Category, Add Customer, Receive payment, etc.) has a back arrow in its header. It closes the popup and keeps you on the same page.
- A logged-in user who opens /login (or /) is sent to the Dashboard. The login page no longer shows inside the app layout after login.

## Files
- templates/base.html: back arrow condition, popup back arrows (script), stylesheet v33.
- static/css/pages.css: popup back arrow style.
- pharmacy/routes/auth.py: logged-in GET /login redirects to the Dashboard.
- tests/test_auth_step4.py: test helper gets the CSRF token from the Dashboard when already logged in.

## Test
- Full suite: 481 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.
