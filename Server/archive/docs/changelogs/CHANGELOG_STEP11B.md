# CHANGELOG - Step 11b (forgot password feature, embossed sidebar, backup and audit polish)

## Forgot password (now a real feature)
- Admin: Users page, new ticket icon "Make one-time reset code" per user.
  Code looks like `ABCD-EFGH`, is valid 15 minutes, works once, and is shown once on screen.
- Only a SHA-256 hash of the code is stored (new table `password_resets`, created automatically).
- `/forgot-password` form: username, reset code, new password, confirm. Password rules apply.
- After 5 wrong tries the user waits a few minutes (uses the existing login lock).
- Wrong username, wrong code and expired code all show the same message (no username guessing).
- Success and failures are written to the audit log (`password.reset`, `password.reset_failed`).
- Admin "set new password now" (key icon) is still there.

## Sidebar
- Embossed look: raised brand card, raised user card, icon tiles, pressed active item with a glowing bar.
- Section labels with a thin fading line; logout is a raised red-tinted tile.

## Backup and Audit Log
- Raised cards, raised chips and buttons, pressed inputs, brand gradient on main buttons.
- Clearer table headers and row hover; stat cards and status pills match the new look.

## Tests
- `tests/test_step11_polish.py`: 20 checks.
- Full mock suite: 566 passed, 0 failed.

## Still open
- Live MySQL test: run `python tests/run_all.py --live` on your PC.
- Browser check: this was checked by rendering HTML, not in a real browser. Look at each page once after copying (Ctrl+F5).
- Customers page table layout is unchanged except the shared icon buttons.
- Step 6 part 2 translations, Content-Security-Policy header.
