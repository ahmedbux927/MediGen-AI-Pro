# MediGen AI Pro: project status and sign-off checklist

Version: v41 (PC app + Android app 1.2 + internet helper).
Automated tests: 1051 passed, 0 failed (mock database; run with `python tests\run_all.py`).

## 0. Final handover (v41)

- Exception safety on all 69 routes (`guarded`), with rollback and friendly messages.
- Sales report can be downloaded as Word (.docx), CSV is not used for sales.
- Profile and name: name, role and deactivation follow the database on every request.
- Missing users columns on older databases are added automatically on start.
- Live MySQL test fixed (test database name is set before config is read). It still has to be run on the shop PC.
- Admin name: change it in My Profile (or run database/rename_admin.sql).

Not verifiable in the build sandbox: the live MySQL test, the Android APK on a phone, the mobile-data internet link, and the thermal printer.

## 1. Done in code (built and tested here)

- Pharmacy core: medicines, batches and expiry, purchases, sales (FIFO, discount, tax, credit, returns), prescriptions, customers, suppliers, supplier returns.
- Reports: sales, profit, stock, expiry tabs, Excel and PDF export, charts (dashboard and reports), timeline playback.
- Security: bcrypt passwords, CSRF on every form, login lock (5 wrong tries), roles (Admin, Pharmacist, Cashier), audit log for all important actions, audit log cannot be edited or deleted from the database.
- Barcode: scanner box for USB or Bluetooth scanners, camera scan on the medicine form and the sales page.
- Offline: local copies of Bootstrap, icons and Chart.js (`static\vendor`); works without internet.
- Backups: daily backup script and Windows task (11 PM), backup guide.
- Always-on: server restarts itself if it stops, starts at login (`scripts\install_always_on.bat`).
- Internet helper: one-click tunnel for testing (`scripts\start_internet.bat`).
- Phone app (Android 1.2): opens the saved server, phone lock (fingerprint, face or PIN), camera permission for barcode scan, brand icon, loading line.
- Help center, video scripts, API with tokens, installable web app (PWA).

## 2. Needs you (cannot be done in the sandbox)

These steps happen on your PC or phone. Tick each one when done.

- [ ] A. Replace the project with the v31 full zip (see REPLACE_HERE_FIRST.txt). Keep `.env`, `backups` and `static\vendor`.
- [ ] B. `python -m pip install -r requirements.txt` and `python tests\run_all.py` show `0 failed`.
- [ ] C. Real database test: `python tests\run_all.py --live` (needs MySQL running and the TEST_DB_* settings).
- [ ] D. Separate database user: run `database\create_app_user.sql` (see `docs\DB_USER_SETUP.md`), change `.env` to `medigen_app`, and change the root password.
- [ ] E. Always-on check: restart the laptop, log in, and open `http://127.0.0.1:5000`.
- [ ] F. Android APK: build in Android Studio (Build > Build APK(s)), install on the phone, check: opens the saved server, fingerprint or PIN lock, camera scan works (needs https, see G), and reports download.
- [ ] G. Internet test: run `scripts\start_internet.bat`, open the https address on mobile data, and check login and one sale.
- [ ] H. Data check: enter real categories, suppliers, customers, medicines and stock. Make a sale, a return, and a purchase. Compare the report totals with your paper register for one day.
- [ ] I. Print check: one thermal receipt from the sales page (80mm printer).
- [ ] J. Backup check: run `scripts\backup_db.bat` and open the new `.sql` file in `backups`.

## 3. Known limits (be aware)

- Camera barcode scan works only on https (the internet address or the PC itself). On the plain WiFi address (`http://192.168...`) the phone camera is blocked by the browser. The USB or Bluetooth scanner works everywhere.
- The quick tunnel address changes each time it starts. For daily use, a stable domain is needed (see docs/INTERNET_ACCESS.md, option 2).
- The server runs only while the laptop is on, charged and connected to the internet. A dedicated PC is recommended for a 24-hour shop.
- The app needs the PC for data. It is not an offline app that keeps its own data on the phone.
- The Android code passed a syntax check here but was not compiled with the Android SDK. Step F is the real test.
- Reports and tax summary: confirm the format with your accountant before you rely on it.

## 4. Next phase (not built yet)

These are design and feature items. They change the look and the settings, so they need your choices.

- Dark and light mode (switch in the profile menu).
- Tile-style home screen with big icons for each module, and a clean login screen.
- User settings: name, photo, change password, and per-user phone unlock (fingerprint or face) setting.
- App settings page: shop name, receipt footer, tax, currency and language.
- Stable internet address with your own domain.
- Offline app with its own phone database (bank-style). This is a large change and is not recommended until the current version has been used for a few weeks.

## 5. Sign-off

The project is ready to use for your shop when A to J are all ticked, and the Android app works on your phone.
