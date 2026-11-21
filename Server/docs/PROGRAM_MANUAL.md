# MediGen AI Pro - Program Manual (v100.00)

This manual is the AI assistant's knowledge base and the staff quick reference.
The online AI receives a condensed version of this map (no shop data is ever sent).

## Start and stop
- Start: double-click `START_MEDIGEN.bat` (starts the waitress server, waits until
  it answers, opens the workbench in the browser at http://127.0.0.1:5000).
- Stop: `STOP_MEDIGEN.bat`. Auto-start at Windows login: `SETUP_AUTO_START.bat` (once, as Administrator).
- Other shop PCs: set `APP_HOST=0.0.0.0` in `.env`, allow port 5000 in Windows Firewall.

## Login
- Username + password. After repeated wrong passwords the login locks for a few minutes.
- **Remember me** keeps THIS PC signed in for 30 days (hashed token, not the password).
  Logout ends it. Passwords: minimum 8 characters, letters and numbers.
- Forgot password: on the shop PC run `python reset_password.py`, or use the
  Forgot Password page with the Admin's one-time code.
- Roles: Admin (everything), Pharmacist (no Reports/Users/Settings money rules),
  Cashier (POS; discount capped by the Settings limit; no cost prices).

## Dashboard
Today's sales and profit, this month, low stock, out of stock, expiring batches
(30/60/90 days), cash in hand, customer credit. Cards link to filtered lists.

## Catalog and medicines
- Product sections: Medicines, Syrups, Creams & Ointments, Drips & Injections, Bandages & Care.
- Medicines: add, edit, soft-delete (Admin, with confirmation; bills stay), bulk edit,
  categories, shelf location, barcode (one barcode = one medicine), reorder level.
- Import products from CSV, Excel, PDF or Word (Products > Import).
- Batches: FIFO (oldest expiry sells first), expiry tracking, write-off, reconcile.

## Sales (POS)
- New Sale: search by name or scan barcode; quantity; discount in % or Rs
  (Cashier limit from Settings); tax from Settings; payment cash/card;
  a balance (udhaar) needs a customer; hold and resume bills.
- A repeated submit with the same client id never creates a second sale.
- Receipts: A4 invoice and 80 mm thermal, both with shop name, phone and footer.
- Returns: from the Sales list; stock returns to the SAME batch; refund adjusts
  the customer's balance. Saved sale totals are never edited - corrections use returns.
- Cash drawer and expenses track the day's cash.

## Purchases
- New Purchase / purchase orders: supplier, items, batch number, expiry, cost.
  Receiving creates batches and adds stock. Supplier ledger shows balances.
  Purchase suggestions and forecast help reorder; drafts can be saved.

## Prescriptions
Add with photo upload, scan review (OCR), doctor and customer, dispense into a sale,
controlled-drug register for scheduled medicines.

## Customers and suppliers
Records, quick-pick by phone number at POS, customer dues (udhaar), customer portal PIN.

## Reports (Admin)
Sales, profit, stock, expiry, tax summary and purchases for any date range.
Export: CSV (UTF-8 with BOM, opens in Excel), Excel, PDF, Word.
Data Quality page: duplicate barcodes, zero prices, stock mismatches, sync conflicts.

## AI assistant
- The built-in assistant answers stock, sales, expiry and how-to questions offline.
- Online AI (Gemini only - key saved on the Settings page or in `.env`)
  answers the rest, knows this manual's program map, and every online answer
  carries: "Please verify with a licensed pharmacist before any clinical decision."
- The assistant never sends customer, patient, sales or stock data to the provider.

## v90.00 changes
- **Medicine knowledge base** (`medicine_knowledge.py`): 116 common medicines with uses,
  common side effects and warnings. The assistant answers "what is X used for",
  "X kis liye hai", "side effects of X" fully offline - by generic or brand name -
  and adds the shop's stock line when the shop sells it. General information only;
  the prescription and pack leaflet always win.
- **Natural how-to matching:** guide questions no longer need the exact words
  "how to" ("How do I take a backup?" works). Data questions (udhaar list,
  expiry discount ideas) still get data answers.
- **Software questions:** "what can this software do / program features" gives a
  full overview of modules, roles and how the system runs.
- **Signature theme** (`static/css/v90-theme.css`): emerald gradient sidebar,
  glass top bar, gradient KPI cards and login backdrop. Loaded last.
- **Remember me confirmation:** after a remembered login the dashboard shows
  "Remember me is ON - this PC will stay signed in for 30 days."
- **Schema fix:** `database/schema.sql` now defines `medicines.is_deleted` -
  a fresh load previously failed at the dashboard views that use the column.
- **Live tests fixed:** the live MySQL tests open the cash drawer before a cash
  sale (required by design since v87.03) and refresh the read snapshot before
  checking the prescription-linked sale. Full suite incl. live MySQL tests:
  verified passing on MySQL 8.0.

## Backup and safety
- Backup: `python scripts/backup_db.py` (real mysqldump; exit code and file size
  checked; a failed run never claims success and never deletes a good backup).
- Self-check: `python scripts/self_check.py` (settings, compile and test report).
- `.env` holds all secrets. Never share it. Version: `Config.APP_VERSION` in config.py.
