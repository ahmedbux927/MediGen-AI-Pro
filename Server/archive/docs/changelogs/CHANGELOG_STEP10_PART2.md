# MediGen AI Pro - Step 10 part 2 (Security finish)

## What changed
- **Medicine CSV export:** the Cost column is blank for Cashier. The cost is removed on the server, not just hidden on screen.
- **Profile photo upload:**
  - Maximum size 2 MB.
  - The file must really be a PNG, JPEG, GIF or WEBP image. A renamed text or script file is refused with a clear message.
- Tests: 16 Step 10 checks (was 11), full suite 543 pass, 0 fail.

## Still planned
- Content-Security-Policy header: needs the inline scripts and styles cleaned up first.

## Files
- Replace: `pharmacy/routes/medicines.py`, `pharmacy/routes/profile.py`, `tests/test_step10_security.py`
- Full project zip also included (safe to replace all files).
