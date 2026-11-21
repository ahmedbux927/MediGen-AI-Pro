# CHANGELOG - Step 11 (full project polish and fixes)

## Forgot password (was: text only, nothing clickable)
- Login page: "Forgot password?" is now a real raised button linking to `/forgot-password`.
- New page `/forgot-password` explains the safe reset path (Admin resets from Users).
- Users page: new key icon (Reset Password) for every user except yourself.
- New route `POST /users/reset_password/<id>`: Admin only, login required, password rules enforced,
  stored as bcrypt hash, written to the audit log (`user.reset_password`). The password is never flashed or logged.

## Error handling
- Raw error text is shown only in DEBUG mode. Normal users and the Admin see the friendly 500 page.
  The full error always goes to the terminal log.
- Test `test_step10_security.py` fixed: it added a route after requests had run (Flask refuses that).

## Neumorphism look
- New `static/css/neu.css` (loaded last, cache-busted `?v=11`): raised logout button, raised icon buttons
  in tables, raised forgot-password button, soft focus and reduced-motion support.
- base.html keeps the light neumorphism sidebar. If your screen still shows a DARK navy sidebar,
  your copy of base.html is older than Step 10b. Replace it from this zip and press Ctrl+F5.

## Tests
- New `tests/test_step11_polish.py` (14 checks).
- Full mock suite: 560 passed, 0 failed (`python tests/run_all.py`).

## Not done in this step (honest list)
- The live MySQL test (`python tests/run_all.py --live`) must be run on your PC.
- Backup, Audit Log and Customers pages still use the existing table design; a full redesign of each is a later step.
- Step 6 part 2 (translating every heading and flash message) is not finished.
- Content-Security-Policy header is not added yet (inline scripts and styles must move first).
- Visual check was done by rendering HTML, not in a real browser. Please check each page once after copying.
