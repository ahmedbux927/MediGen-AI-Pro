# MediGen AI Pro - Project Audit and Overview

Version: Step 7 (prepared 13 October 2026)
Stack: Python Flask, MySQL 8 (Workbench), Bootstrap 5, Chart.js, bcrypt, Flask-MySQLdb

---

## 1. What the system does

A complete pharmacy management system for one shop (single branch):

- Medicines: stock, prices, cost, reorder levels, stock adjustments, search and pagination
- Batches and expiry: batch numbers, expiry tracking, write-off of expired stock, sync with stock
- Purchases: supplier purchases that create batches and update stock automatically
- Sales: discount, tax, credit (udhaar), payments, returns and refunds, receipts
- Prescriptions: doctor prescriptions, edit, delete, print, dispense (make a sale from a prescription), basic allergy warning
- Customers and suppliers: records and quick-add
- Reports: sales and stock reports (Admin)
- Users and roles: Admin, Pharmacist, Cashier, with time-limited login access
- Audit log: a record of important actions and logins (Admin)
- AI assistant (chatbot): offline, answers stock, sales, expiry and customer questions in English and Roman Urdu

## 2. Roles and what each can do

| Feature | Admin | Pharmacist | Cashier |
|---|---|---|---|
| Dashboard, sales (create, view receipt) | yes | yes | yes |
| Sales returns and receive payment | yes | yes | no |
| Discount above 10% | yes | yes | no (limit set in .env) |
| Medicines: view / add / edit / adjust stock | yes | yes | view only (no cost price) |
| Medicine delete | yes | no | no |
| Purchases and batch sync | yes | no | no |
| Batch write-off | yes | yes | no |
| Prescriptions: add, edit, print, dispense | yes | yes | no |
| Prescription delete | yes | no | no |
| Reports | yes | no | no |
| Users | yes | no | no |
| Audit log | yes | no | no |

## 3. Build history (steps)

| Step | Area | Status |
|---|---|---|
| 1 | Base setup: config, .env, schema, README | Done |
| 2 | Security: CSRF, login lock, password rules, session timeout, POST-only delete | Done |
| 3 | Medicines: edit, adjust stock, history, search, pagination, cost and margin | Done |
| 4 | Purchase with batch and expiry, batches page, write-off, sync | Done |
| 5 | Sales: discount, tax, udhaar, payments, returns, FIFO batches, receipts | Done |
| 6 | Prescriptions: list, add, dispense, allergy warning, doctor name fix | Done |
| 7 | Prescription edit and delete, Print/Edit/Delete buttons, audit log | Done |
| 8 | Chatbot Pro (more questions, reorder and expiry tips) | Planned |
| 9 | Settings, backup and restore, 80mm thermal receipt | Planned |
| 10 | Automated tests on a real MySQL database, final bug sweep | Planned |
| 11 | Frontend polish: 404/500 theme, mobile layout, Urdu labels | Planned |
| 12 | Windows desktop application (.exe) | Planned |

## 4. Bugs fixed so far (main ones)

- Sales list showed only the first 50 old sales; now newest first with pagination
- New sale saved an empty sale when stock was short; stock is now checked before saving
- Same medicine added twice in one sale bypassed the stock check; quantities are now combined
- New purchase could save with no items; now rejected
- Login: night-shift access (for example 20:00 to 06:00) was rejected; fixed
- Login crashed for users with no password hash; fixed
- Profile picture: .jfif files were rejected; now allowed, and saved to the correct folder
- Delete and toggle were GET links (could be triggered by a simple link); now POST only with CSRF token
- Records clear needed no password; now the Admin must type their password
- Chatbot 500 error (missing batches route and old app.py running); fixed
- 404 and 500 pages could crash; now safe, and Admin sees the technical error on 500
- Medicine stock badge used fixed numbers (20 and 100); now uses the reorder level of each medicine
- Medicine delete with history showed a raw SQL error; now a clear message
- Reserved word `empty` used as a column alias broke MySQL 8 queries; renamed
- Doctor name "Dr. Dr. Ahmed" on receipts; doctor names are normalised everywhere
- Expired batches could be sold; sales now use only unexpired batches (oldest expiry first)
- Expired batches showed as "Expiring soon" in some cases; status now computed correctly
- Stock and batch totals did not match; sync tool added with preview
- Returns did not give back stock; returns now restore stock and batch quantities
- Revenue counted returned sales; revenue is now net of returns

## 5. Security status

Done:
- CSRF protection on every POST form and AJAX call
- Login lock after repeated wrong passwords (5 tries, 5 minutes)
- Password rules: 8+ characters, letters and numbers, common passwords blocked
- Session timeout (30 minutes idle), session cookie HTTP-only
- Secrets in `.env` (not in code); debug mode off by default
- Passwords stored with bcrypt
- Browser security headers (frame and content-type protection)
- Role checks on every sensitive route (server side, not only hidden buttons)
- Admin password needed to clear records
- Audit log for important actions and login success and failure

Open:
- Login lock is kept in memory: it resets when the server restarts
- No HTTPS (fine on a local network; needed before any internet access)
- Users, customers, suppliers and profile changes are not yet in the audit log
- No automatic database backup yet (planned in Step 9)
- Default admin password from the old system must be changed by the owner

## 6. Audit log coverage

Recorded now: login success and failure, prescription add, edit and delete, sale create, payment received, sale return, medicine add, edit and delete, stock adjustment, purchase create, batch write-off, batch sync.

Not yet recorded: user add, edit, toggle and delete; password change; customer and supplier changes; records clear; profile changes. These are planned for Step 9.

The audit log is read-only in the app (no edit or delete buttons). For strong protection, the database user used by the app should not have DELETE permission on `audit_log`.

## 7. Known limitations

- Allergy warning is a simple keyword check, not a medical system. It does not check drug interactions or doses. The pharmacist must decide.
- Dispensing from a prescription sets quantity 1; the pharmacist must change it (the dosage text cannot be read reliably).
- Reports do not yet export to Excel or PDF (planned).
- Chatbot works with keywords only (no AI model, no internet). Planned improvements are in Step 8.
- The first `cost_price` values were filled from old purchase data; check the cost of important medicines.
- Test purchase order #8 (Rs. 30,000,000) may be test data; review it.
- Layout has been checked in code, not yet on phones or small screens.
- Windows `flask_mysqldb` installation can be difficult; `PyMySQL` is the easier option for the desktop version.

## 8. Testing status

Tests were run with a stub (fake) database, so SQL syntax against real MySQL 8 has NOT been executed in the build environment. Each step was tested with these suites:

| Suite | Covers | Result |
|---|---|---|
| Security | login, lock, CSRF, POST-only delete, password rules, records clear | 25 of 26 pass (1 is an outdated test expectation: `Admin123` is correctly rejected) |
| Medicines | list, search, pagination, edit, adjust, history, delete rules | 23 of 23 pass |
| Purchase and batches | purchase rows, batch merge and conflict, write-off, sync | 29 of 29 pass |
| Sales | FIFO, discount, tax, udhaar, payments, returns, receipts, roles | 47 of 47 pass |
| Prescriptions | doctor name, allergy warning, add, dispense, validation | 41 of 41 pass |
| Prescription edit, delete, audit | edit, locked edit after dispense, delete rules, audit page | 29 of 29 pass |
| Chatbot | stock, sales, expiry, alerts, counts, guides | passes; no runtime errors |

Important: before going live, run the manual checklist in section 10 on the real database.

## 9. Risks and recommendations (priority order)

1. **Backup first.** Export the database every day (Workbench Data Export, or the backup feature in Step 9). Keep copies on another drive.
2. **Test on a copy.** Restore a backup into a second database name and test new features there before using the main one.
3. **Change the default admin password** and create separate logins for each staff member (never share one login).
4. **Keep `.env` private.** Do not upload it to the internet or share it.
5. **Use the audit log** to check unusual deletes, discounts and returns every week.
6. **Set database permissions:** the app user should not be `root`. Create an app user with only the rights it needs.
7. **Use a production server** (waitress) instead of the development server when used daily.
8. **Use Git** (or dated ZIP copies) so every change can be undone.
9. **Automated tests on real MySQL** (Step 10) so that SQL errors are caught before you see them.
10. **Consider HTTPS** before the system is reachable from outside the shop network.

## 10. Manual checklist (run once on the real database)

1. Login works with the new admin password; wrong password 5 times gives a lock.
2. Medicines: add, edit, adjust stock (remove and add), view history; delete a medicine with history shows a clear message.
3. Purchase: add a medicine with batch and expiry; batches page shows it; "Sync batches" preview looks correct.
4. Sale: sell 2 medicines, one with a discount; receipt shows subtotal, discount and total; stock goes down.
5. Udhaar: sell to a customer and receive less than the total; the balance shows on the sales list; receive the rest.
6. Return: return one item; stock goes up; refund message is correct.
7. Prescription: add, edit (doctor, medicine), print the receipt, dispense it to make a sale; try to edit the medicines after dispensing (must be locked); try to delete it as Admin (must be blocked after dispensing).
8. Audit log: the actions above appear with the right user name.
9. Cashier: cannot see Prescriptions, Returns, Purchases, Reports or Audit Log.
10. Restart the server: login still works; the database auto-update message appears.

## 11. Files in this release (Step 7)

- `app.py`, `config.py`, `chatbot_engine.py`: main code
- `templates/`: all pages (prescriptions, edit_prescription, audit_log, base and others)
- `fix_doctor_names.sql`: OPTIONAL clean-up of stored doctor names (the app already shows names correctly)
- `.env` (settings and secrets), `create_admin.py`, `schema.sql`, `sample_data.sql`
