# Final hardening (v34 -> v35)

## What changed
- **Exception safety on every route**: new `guarded()` decorator in `pharmacy/lib.py`, applied to all 69 routes.
  - Unexpected errors are logged in full on the server.
  - The database transaction is rolled back.
  - Users see a short message: a 500 page for normal pages, a JSON error for `/api/` and `/chatbot/api`, and a flash message plus redirect for failed form posts.
  - Form-post redirects only go back to pages on this same site (no redirect to other websites).
  - Normal HTTP errors (404, 401, redirects) pass through unchanged.
- **Security fix**: the stock history table on the medicine page now escapes the note, reason, user and date fields before showing them (stored XSS guard).
- **Desktop app**: if the browser cannot open automatically, the app now prints the address to open by hand.
- **Logging**: the shop-name fallback in reports now logs the error.

## Tests
- `tests/test_guarded.py` (5 tests): friendly 500, POST flash/redirect, no external redirect, HTTP errors pass through, JSON errors for API.
- `tests/test_history_escape.py` (3 tests): escape guard for stock history.
- Full suite: 1036 passed, 0 failed (with the mock database).

## Still needs the real PC
- Live MySQL test (`python tests\run_all.py --live`)
- Android APK build and phone test
- Mobile-data test of the internet link
