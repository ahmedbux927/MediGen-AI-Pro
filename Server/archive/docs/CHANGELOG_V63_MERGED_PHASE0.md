# MediGen v63 - merged project (Phase 0)

## What this zip is
- Backend: v54 backend (Step 32): error codes, POS checkout API, AI agent tool layer (migration 007), 1341 tests.
- Frontend: the approved light shell, login redesign, dashboard, phone pass and report chart switch (merged v62 line).
- Freeze manifest regenerated for the frontend.

## Changes in this step
- User add error now shows a code: "User could not be added. Error E-302." (ERROR_CODES['user_add']).
- File logging: app errors and warnings are written to logs/medigen.log next to the app (2 MB per file, 5 old files kept).
  Before this, errors only went to the console, which the exe does not show.

## Test
- tests/run_all.py: 1341 passed, 0 failed (mock database).
- Not run: live MySQL (--live), Windows EXE build, Android APK, thermal printer, real Chart.js, Bootstrap Icons.

## Shop PC checklist (tick each one)
1. Stop the old server and MediGenAIPro.exe. Keep .env, backups and static\vendor safe.
2. Extract this zip to a new folder. Copy .env, backups and static\vendor back.
3. python -m pip install -r requirements.txt
4. python tests\run_all.py  (expect 1341 passed)
5. python tests\run_all.py --live  (MySQL running)
6. Start the app. Login. Check icons and Chart.js charts on Dashboard and Reports.
7. Add a user. If it fails, open logs\medigen.log and send the lines.
8. Forgot password: admin creates a reset code, user sets new password.
9. Delete a user that has sales (should become OFF, not deleted).
10. Print a receipt on the thermal printer.
11. Build the EXE and test the installer.

## Known gaps (not done here)
- Forgot password needs admin reset code (no email/SMS).
- Agent route and UI not built yet (tools exist, no route).
- Camera barcode scan, mobile app, prescription OCR, online store: later phases.
