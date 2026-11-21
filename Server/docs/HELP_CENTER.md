# MediGen AI Pro - Help Center

Quick answers for pharmacy staff. Menu names match the sidebar.

## 1. Getting started
- **Start the app:** double-click the MediGen shortcut (Windows), or run `python desktop.py` in the project folder. The browser opens the login page.
- **First admin:** run `python create_admin.py` once. Then log in with that account.
- **Other PCs or phones on the same WiFi:** set `APP_HOST=0.0.0.0` in `.env`, then run `python app.py`. Open the `Same WiFi` address it prints (`http://<PC-IP>:5000`) on the device. Allow port 5000 in Windows Firewall.
- **Page looks old after an update:** press **Ctrl+F5**.
- **Back arrow:** top bar. It is hidden on the Dashboard and the login page.
- **Log out:** red button at the bottom of the sidebar, under My Profile.

## 2. Roles
| Role | Can do |
|---|---|
| Admin | Everything, including Users, Records Clear, Reports, Settings and deleting suppliers or categories |
| Pharmacist | Medicines, batches, sales, purchases, prescriptions, customers, suppliers, alerts, reports |
| Cashier | Sales, customers, dashboard. Discounts above the Settings limit are refused |

## 3. Medicines and stock
- **Add a medicine:** Medicines > Add. Name, category and price are required. Enter opening stock if you have it.
- **Change stock:** Medicines > Adjust. Choose In or Out and a reason. Out cannot go above the stock. History is kept for each medicine.
- **Delete a medicine:** only if it has no sales or purchase history. Otherwise set stock to 0 with Adjust.
- **Export:** select medicines and export to CSV.

## 4. Batches and expiry
- **Batches & Expiry:** shows every batch with days left. Status is Expired, Soon (within 90 days), OK or Empty.
- **Expired batches are never sold.** To remove them, press **Write off** on the batch. The stock history is updated.
- **Mismatch:** if batch totals do not match the medicine stock, Batches shows a warning. Admin uses **Reconcile** to fix it.

## 5. Sales (POS)
1. Transactions > New Sale. Add medicines and quantities. Stock is taken from the oldest-expiry batch first.
2. Add a discount (Rs. or %) if needed. Tax follows Settings.
3. Enter the amount paid. If the customer pays less, the balance goes to **Customer Dues** (udhaar). A customer is required for udhaar.
4. Print the 80 mm receipt.

Allergy warnings are shown before saving. They do not block the sale. The pharmacist decides.

## 6. Returns
- **Sale return:** open the sale, pick the items to return. The refund and stock are updated.
- **Supplier return:** Transactions > Supplier Returns. Use it for expired, damaged, recalled or other stock sent back to the supplier. Quantity cannot be more than the batch has.

## 7. Purchases
- Transactions > Purchases > New Purchase. Enter batch number and expiry (must be a future date). The stock and cost price are updated.

## 8. Prescriptions
- Prescriptions > New. Choose the customer, doctor, and medicines with dosage and days. Doctor names are cleaned automatically (Dr. is added once).
- A prescription can be loaded into a new sale from its page.
- An open prescription can be edited or deleted. A dispensed one cannot be deleted.

## 9. Alerts
Alerts lists low stock, expiring batches (90 days) and expired stock with units left. Use it each morning.

## 10. Reports
- Reports has 5 tabs: Overview, Sales, Profit, Stock, Expiry. Use the date presets or pick dates.
- **Export:** Excel (.xlsx) and PDF from the Sales tab. The Tax summary is available as Excel and PDF too.
- **Tax summary:** gives the tax collected per day. It is a summary only. Confirm the rate and filing rules with your tax advisor.

## 11. Backups
- Run `scripts\backup_db.bat` to make a backup in the `backups` folder. The newest 30 are kept (set `BACKUP_KEEP` in `.env` to change).
- Schedule it with Windows Task Scheduler (daily). Copy backups to a USB drive or cloud folder.
- Restore steps: see `docs\BACKUP_RUNBOOK.md`.

## 12. Users and security
- **Users** (Admin): add users, change roles, set night-shift access hours, deactivate.
- **Forgot password:** the user asks the Admin for a one-time code (valid 15 minutes). The Admin creates it from Users.
- Five wrong logins lock the account for 5 minutes.
- **Records Clear** (Admin) deletes history. It needs the Admin password and cannot be undone. Make a backup first.

## 13. Settings
Shop name, address, phone, receipt footer, tax rate (0-30%) and the cashier discount limit (0-100%).

## 14. Other shop PCs and API
- **Other PCs in the shop:** set `APP_HOST=0.0.0.0` in `.env`, restart, then open `http://<workbench-IP>:5000` in the browser on the other PC. (v88.00: the Android phone app was removed - see `REMOVED_PHONE_CODE.md`.)
- **API:** Admin or Pharmacist token from `python scripts\create_api_token.py "Label" Admin`. Read-only, under `/api/v1/`.

## 15. Troubleshooting
| Problem | Fix |
|---|---|
| `ImportError` on start | Replace the whole `pharmacy` folder with the one from the zip. |
| Page shows old style | Ctrl+F5 |
| "Could not connect to MySQL" | Check `.env` (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME). Make sure the MySQL service is running. |
| Cannot open from phone | Use the PC's IP and port 5000. Allow Python through Windows Firewall on Private networks. |
| Phone install button missing | Install needs HTTPS or localhost. Plain `http://192.168...` does not allow install. |
| Wrong totals in a report | Compare with Batches and Stock. Use Batches > Reconcile if stock and batches differ. |
| Forgot admin password | Run `python create_admin.py` on the PC to make a new admin. |
