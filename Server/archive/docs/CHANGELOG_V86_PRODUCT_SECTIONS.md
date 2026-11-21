# MediGen v86 - Product sections, cart and CSV load

## New
- Five product sections, each with its own page and list: Medicines, Syrups & Suspensions, Creams & Gels, Drip & Injection, Bandages & Other.
- /products - hub with one card per section (items, in stock, low, expiring in 60 days, no stock, units sold today).
- /products/<section> - search, barcode box (adds straight to the cart), quantity + Add to sale, edit, remove (only when no sale/batch/adjustment history), load CSV, add one item.
- Quick sale cart (session 'sale_cart', max 40 lines): items from any section; Open sale button passes the cart to the sale screen; the cart is cleared after a sale is saved.
- CSV load per section (UTF-8, max 2 MB, max 5000 rows). Prices and stock in the file are ignored; stock comes from Purchase. Duplicate names inside a file are kept once; names already in the database are skipped; a barcode already in use is stored without barcode.
- Drip section accepts only injection / IV drip / infusion forms; a non-drip row stops the file with a message.
- Dashboard: product section table (links to each section) above the stock and expiry block.
- Medicines list: Sell link per row; dosage form selects now list every section form.
- /drip redirects to the Drip & Injection section.

## Checks
- tests/test_product_sections.py (39 checks, no MySQL): section mapping, CSV parsing of syrups / creams / drip fixtures, error messages, import behaviour, route guards, cart limits, wiring.
- python tests\run_all.py: 1627 passed, 0 failed (static/mock; no MySQL in the build sandbox).

## Not yet verified on the shop PC (MySQL + browser)
- Syrup, cream and bandage CSV loads against the live database.
- Section pages, cart, Open sale, and the sale saved from the cart.
- Dashboard section table layout on a phone-width screen.
- POS / app checkout still saves drip routes as 'Not set' (counter sale only has the route choice).

## Removed / dead
- templates/drip.html is no longer rendered (kept until confirmed safe to delete).

## v86.1 (shop feedback)
- Edit product: shows every batch (batch no, expiry date, quantity) and the batch total; warns if batch total and stock total differ.
- Section page: "Clear unused items in this section" (Admin/Pharmacist). Removes only items with no sales, stock or drip history.
- Section page: zero-stock rows show "Buy stock" (link to Purchase) instead of a disabled Add.
- Known: sale dropdown lists only items with stock > 0. Items loaded from CSV stay at 0 until Purchase.
- Not built yet: PDF list import, photo/camera list import (OCR), world product catalogue.

## v86.2
- Section pages: Load list (CSV or PDF) and Add one item are now at the top, above the search box.
- Import accepts PDF: tables with a header row are read as a CSV list; a PDF without table lines is read line by line as product names. Broken or image-only PDFs are refused with a message (scanned PDFs need OCR, not built yet).
- Each in-stock row has a tick box. "Sell selected" adds every ticked product (1 piece each, stock checked) to the sale and opens the sale screen with the total.

## v86.3
- Sidebar: one link per section (Medicines, Syrups & Suspensions, Creams & Gels, Drip & Injection, Bandages & Other), then Product Overview.
- Each section page: Export CSV (same columns the loader reads), Receive stock form (product, quantity, batch, expiry, cost). Receive adds to a batch, raises the stock and writes stock history. Expiry must be in the future.
- Medicines page: Import list button (opens the section loader, CSV or PDF).
- Sale screen: typing a name (not a barcode) and pressing Enter adds the item when exactly one in-stock item matches; several matches show a count.
- Not built yet: multi-select on the Medicines table itself; sidebar reorder of Transactions group; scanned-PDF OCR.

## v86.4
- Add (per row) and barcode add on section pages now open the sale screen with the item in it.
- Medicines table: tick boxes (existing) + "Sell Selected" button: ticked medicines go to the sale screen with total.
- Scanned PDF (no text layer): each page is read with Tesseract (same engine as the prescription reader), max 20 pages. Without Tesseract the user gets a clear message.

## v86.5
- Fix: Edit product page gave 500 (the batch query was placed after the except block's return, so it never ran). Moved inside the try. Test added.

## v86.6
- Sale screen: the item dropdown is grouped by section (Medicines, Syrups & Suspensions, Creams & Gels, Drip & Injection, Bandages & Other).
- Sale screen: product picker above the scan box. Section tabs with counts, a search box, and one card per in-stock item (name, form, price, stock left). Click adds one piece. Barcode scan and card click use the same add function, so stock checks are identical.

## v86.7
- Dashboard: "Last 7 days" bar per section (animated, off when the PC asks for reduced motion).
- Section pages: 15 / 50 / 100 rows per page, Prev / Next, "Showing x-y of total".
- scripts\schedule_daily_backup.bat: run once as Administrator; registers a daily backup at 23:30 in Windows Task Scheduler.
- Sale screen: phone/tablet layout (cards stacked, 2-column picker).

## v86.8 (plan step 1, part)
- Section pages: same stat cards as Medicines (total, in stock, low, out, expiring 60 days), same page header. Counts are over all rows of the section, not just the current page.
- Not yet: the Medicines page itself still has its own layout (search debounce, bulk bar); full single-component unification is the next step.

## v86.9
- Medicines page: choice is now 15 / 50 / 100 per page (was 10 / 15 / 25 / 50). Default 15. Row numbers (#) continue across pages.
- Section pages (Syrups, Creams, Drip, Bandages): row numbers (#) continue across pages; numbered page links (1 2 3 ... with Prev/Next); 15 / 50 / 100 per page selector.

## v86.10
- Sales list: 15 / 50 / 100 per page (default 15, was fixed 20), row numbers (No.), per-page choice kept when moving between pages and with search and date filters.

## v86.11
- 80 mm receipt: lines grouped under section headings (Medicines, Syrups & Suspensions, Creams & Gels, Drip & Injection, Bandages & Other), with a subtotal and units per section when the sale has more than one section. Last line shows total units and number of sections. Totals block unchanged.

## v86.12 (visual redesign, step 1: dashboard)
- Dashboard: visible gradient background behind the cards; cards are frosted glass (blur) with a lift on hover; cards enter one after another; dark-mode colours; all motion off for reduced-motion users.
- Still to do: same background and card style on the other pages; chart animation variants.

## v86.13
- Deleted templates/drip.html (dead page, no route rendered it). Tests that read it now check the section page or the schema.

## v86.14 (step 1: sale speed and errors)
- Every unexpected error now gets an ID (ERR-xxxxxx). The same ID is shown on the screen (flash, 500 page, JSON) and written in logs\medigen.log. Fixed codes (E-102 etc.) keep their wording.
- Sale screen: barcode box is focused when the page opens (scan at once). F2 scan, F3 new line, F9 complete (already there).
- To find an error: copy the ID from the screen and search logs\medigen.log for it.

## v86.15 (step 1, part 2: keyboard-first sale)
- After every add (scan, name, card) the cursor returns to the barcode box and the box is cleared.
- Enter in a quantity box returns to the barcode box.

## v86.16 - Prescription photo: gallery + stock check + bill available
- New: "Choose a photo from the gallery" input next to the phone camera input (rx_scan.html, rx_scan route accepts either).
- New: each medicine row on the review page shows "In stock: N" or "Not available: will not be billed".
- New: "Save and bill available items" button. It saves the prescription and opens the sale with the prescription.
- Changed: prescription sale prefill names the out-of-stock medicines in the warning (sales.py).
- Tests: full suite 1675/1675.

## v86.17 - Reports: sections and slow movers
- New: Reports → Sections tab (units, revenue, profit and share per product section for the period).
- New: Reports → Slow movers tab (items in stock that did not sell in the period, with value at price).
- Alerts page (low stock, expiring 90 days, expired with units) already existed; no change.
- Tests: full suite 1675/1675.

## v86.18 - Design unify: shared page header and stat cards
- New: static/css/inventory.css holds the page header and stat-card styles, used by Medicines and all product section pages.
- Removed: duplicate stat-card CSS from medicines.html and products.html. Also fixed a broken selector in products.html that leaked .pd-tabs styles.
- Tests: full suite 1675/1675.

## v86.19 - Dashboard look on Sale, Customers and Reports
- New: static/css/page-look.css. Soft gradient background and frosted cards, same as the dashboard.
- base.html: adds class "page-look" to body only for new_sale, customers and reports. Other pages are unchanged.
- Tests: full suite 1675/1675.

## v86.20 - Dashboard look on Medicines and product section pages
- base.html: "page-look" class now also for medicines, products_section, products_hub and products_edit.
- Tests: full suite 1675/1675.

## v86.21 - Dashboard look on Batches, Prescriptions, Purchase, Supplier Returns, Alerts and Settings
- base.html: "page-look" class added for batches, prescriptions, add_prescription, purchase, supplier_returns, alerts, settings_page.
- Tests: full suite 1675/1675.

## v86.22 - Android phone setup guide
- New: ANDROID_PHONE_SETUP.md (LAN address, firewall port 5000, Add to Home screen).
- Note: over plain http on the LAN, the offline service worker does not register. Offline on phone needs https (later step).
- Manifest and icons checked: OK.

## v86.24 - Purchase suggestions
- New: /purchase/suggestions (sidebar "Suggestions" under Purchase). Lists items that are low (stock <= reorder level) or run out within 14 days, based on the last 30 days of sales.
- Suggested qty = enough for 30 days or reorder level, minus stock now. Est. cost uses cost price. CSV export included.
- New: tests/test_purchase_suggest.py (6 checks, stub cursor).
- Note: 3 checks in test_prescription_edit_audit.py and test_reports_exports.py still expect the audit page removed (Step 11O). The audit viewer (routes/audit_view.py, v86.23) was added separately and needs a decision.

## v86.25 - Medicine delete message
- Changed: Medicines delete message now names all blockers (sales, purchases, stock batches, stock adjustments). Before, it only said sales or purchases.
- Test updated: tests/test_coverage_medicines.py.
- Duplicate names: add and edit already block a repeated name. Check the shop DB for old duplicates (see the duplicate query in the reply).

## v86.26 - One page, live search, direct import with quantity
- Medicines page and product section pages: no 15/50/100 pager. All items on one page.
- Medicines page: search filters rows as you type (name, category, form, barcode). No reload.
- Medicines page: "Import list" opens the file picker directly; the file uploads on pick.
- CSV/PDF import: a quantity (or stock / qty) column sets opening stock. Empty = 0. Negative or non-number rows stop the file with the row number. Stock history gets an "Opening stock" entry.
- Tests updated for the new behavior (test_product_sections.py). Audit checks still pending the audit decision.
- Still open from earlier: delete of medicines with batches, and the medicine form category filter.

## v86.27 - Delete clears stock; medicine categories only; live section search; audit viewer removed
- Delete (Medicines page and section page): if there is no sale, purchase, prescription or drip record, the medicine is deleted with its stock batches and stock entries. With history, it is kept and the message says why.
- Medicine form: category list shows only medicine categories (Syrups, Creams & Gels, Injections, Bandages & Other are hidden). An item's own category still shows on edit.
- Section pages: search filters rows as you type.
- Audit viewer removed (routes/audit_view.py, templates/audit.html, sidebar link). Its tests are gone with it.
- Tests: full suite 1681/1681.

## v86.28 - Delete message
- Delete: stock does not matter. Only sale, purchase, prescription or drip history blocks a delete. Message shortened.
- Prescription photo flow not changed in this step (doctor name and patient name still required; needs a sample photo and the shop PC OCR check).
- v86.28b: stock never blocks a delete. The message only names sales/purchase/prescription/drip history.
- v86.28c: fixed message typo ('This medicine has sales, so it cannot be deleted.').

## v86.29 - Delete hides the medicine; bills and records stay
- Delete (Medicines page and section pages) always works, whatever the stock or history.
- Delete sets medicines.is_deleted = 1 and renames the item to "<name> (deleted <id>)", clears its barcode. Name and barcode are free again.
- The column is added automatically on startup (core.ensure_medicine_hidden_column). Sales, purchases, prescriptions and reports keep their old rows; old bills show the "(deleted ...)" name.
- Hidden from: Medicines list and counts, section pages and overview, sale picker, barcode lookups (sale, POS, products), purchase picker, prescription and photo pickers, batches list, low stock and stock check reports, dashboard count.
- Not yet filtered: CSV export of medicines, the agent/chatbot search, the API lists (api.py), expiry report and the database views (v_low_stock, v_expiring_soon used by the dashboard). Tell me if you want these too.
- Tests updated for the new delete (test_coverage_medicines, test_security, test_repos). Full suite 1681/1681.

## v86.30 - Search box on Medicines page does not reload
- Removed the old auto-submit on the Medicines search box. It reloaded the page every time you paused, and the cursor jumped out.
- Search filters the list as you type (medFilter). A clear (x) button and a live count ("Found N of M") sit under the box.
- Section pages: search is live too (secFilter), with no auto-submit.
- Tests: full suite 1681/1681.

## v86.31 - Medicines action buttons on one row
- Sell, Edit, Adjust Stock, Stock History and Delete sit in one line, same size, with hover lift and colour per action.
- Tests: full suite 1681/1681.
- v86.32: build marker 'Build v86.32' on the Medicines page, so you can confirm the new build is running.

## v86.33 - Selection bar and action row
- Selection bar: the button is "Clear all" (unselects every row and the header tick). The bar no longer sits under the floating assistant button.
- Action buttons: forced onto one line (the older wrap rule was overriding it).
- Build marker now says v86.33.

## v86.34 - Delete selected (bulk delete)
- Selection bar: "Delete selected" (Admin only), with a confirm box showing the count.
- New route POST /medicines/bulk-delete: hides every ticked medicine (same rule as the single delete). Bills and purchases stay.
- Build marker now v86.34. Tests 1681/1681.

## v86.35 - Add Medicine: barcode scanner and camera
- Barcode field in Add New Medicine: a USB/Bluetooth scanner types the code and presses Enter; Enter no longer submits the half-filled form.
- A code already used by another medicine is refused at once, with the medicine's name shown.
- Otherwise the cursor moves to the next empty required field, and the form saves when every required field is filled.
- Camera button (replaces the old Scan button in the Add form) reads the barcode with the camera and works the same way as Enter.
- Edit form keeps its Scan button.
- Barcode map comes from repos/medicines.barcode_map (no raw SQL in routes).
- Build marker: v86.35.

## v86.36 - Section pages look and work like Medicines
- Syrups, Creams, Drip, Bandages and Overview use the Medicines layout: toolbar, live search with count, one table, row checkboxes, Clear all, Sell Selected, Delete selected (Admin), Export Selected.
- Row actions: Add one to sale, Edit, Receive stock, Delete (Admin), in one row.
- Add item moved into a popup; Import list is in the toolbar.
- Medicines CSS moved to static/css/medicine-look.css (shared by both pages).
- Delete selected on a section page returns to that section page.
- Export Selected exports only the ticked rows (section CSV export too).
- Barcode box on section pages kept (scan and Enter adds one to the sale).
- Build marker: v86.36.

## v86.37 - Section stat cards open their list again
- On Syrups, Creams, Drip, Bandages and Overview, the top cards (Total, In stock, Low, Out, Expiring) filter the list on click, as on Medicines. This was lost in v86.36.
- Search and the stat filter work together.
- Build marker: v86.37.

## v86.38 - Hidden (deleted) medicines left out everywhere
- Left out of: API medicine list, agent/chatbot search and lists, drip report, stock count, slow movers report, purchase suggestions, batch mismatch count, CSV export, expiry rows, and the dashboard views (v_low_stock, v_expiring_soon; re-created at startup).
- Bills, purchases and history keep the medicine as before.
- New test: tests/test_hidden_filter.py.
- Build marker: v86.38.

## v86.39 - Section pages: filter tabs like Medicines, section tabs removed
- Removed the section tab row (Medicines, Syrups, Creams, Drip, Bandages) from section pages. The sidebar already has these links.
- Added All / In Stock / Low / Out filter tabs, same as the Medicines page. They sync with the stat cards.
- Build marker: v86.39.

## v86.40 - Action buttons always fully visible
- Actions column is wider (232px) and the 5 buttons (Sell, Edit, Adjust, History, Delete) fit on one row. Buttons are 34px.
- The table card scrolls sideways instead of cutting off the right side (Delete was hidden before).
- Same order on Medicines and section pages.
- Build marker: v86.40.

## v86.41 - Edit selected (bulk edit) and Receive stock popup
- Bulk bar (Medicines and section pages): new "Edit selected" button (not for Cashier).
- Popup changes category, dosage form, expiry date (all batches of the chosen items) and price. A blank field does not change.
- Dosage form decides the section: an item moved to another form appears in that section.
- Refused: empty form, unknown dosage form, negative price. Every change goes to the audit log.
- Receive stock is a popup (toolbar button, or the receive icon in a row opens it with that item chosen). The card at the bottom is gone.
- Build marker: v86.41.

## v86.42 - Edit selected: no browser confirm, live summary
- Removed the browser "Update N item(s)?" box. The popup shows what will change and Save stays off until at least one field is filled.
- Expiry only for all selected items works in one save.
- Build marker: v86.42.

## v86.43 - Import: lenient CSV, photo import, friendly messages
- CSV: name headers recognised in more forms (medicine, item, product, title, drug...). Works with ; or tab separators and with Windows (cp1252) Excel files. No name header: the first column is used, with a warning.
- Bad rows are skipped and listed as warnings (line number and reason). The good rows still load. Only a file with no usable item is refused.
- Quantity reads "10 pcs" as 10. Strength "0", "nil" and similar are ignored.
- List numbers ("1.", "2)") and "Rs. 120" price tails are removed from names.
- Photo import: "Camera photo" button (camera) or Import list (gallery). Needs Tesseract OCR: see TESSERACT_INSTALL_ROMAN_URDU.md. Without it the user gets a clear message.
- PDF: unchanged (tables, text lines, scanned PDFs through Tesseract).
- Build marker: v86.43.

## v86.44 - PDF import for any layout
- Bordered tables, borderless tables (no lines), plain text lists, and scanned PDFs (picture pages, read with Tesseract) all import.
- Each page is read on its own. A scanned page no longer blocks the rest.
- Table header can be any name column (medicine, item, product, drug...). Titles, dates ("27 Oct"), totals and page numbers are skipped.
- PDF size limit is 10 MB (CSV stays 2 MB).
- Build marker: v86.44.

## v86.45 - Bulk edit expiry fix and strength field
- Bulk expiry now applies to every selected item. Items that had stock but no batch get one batch named OPENING holding their current stock, so the expiry shows. Items with no stock and no batch are skipped and the message says so (expiry is set when stock is received).
- Bulk edit popup has a Strength field (max 60 characters). Blank means no change.
- Result message shows how many batches changed, how many items got an OPENING batch and how many were skipped.
- Build marker set to v86.45.

## v86.46 - Data Quality report and guard on remaining routes
- New Data Quality page (sidebar, Admin section; Admin and Pharmacist can open it). Read only. Shows: same-name duplicates, no category, no or zero price, no dosage form, bad strength (0, dash, or bare number), repeated category names, stock with no batch, and stock vs batch mismatch. Shows a health score (clean medicines out of total). Deleted medicines are always skipped.
- @guarded added to the POS checkout API route and the two prescription scan save/cancel routes (they now show a friendly message on unexpected errors instead of a crash).
- Build marker set to v86.46.
- Not in this version: database backup button, supplier ledger, owner mobile dashboard, offline mode, Urdu voice add, activity log filter.

## v86.47 - Supplier Summary
- New Supplier Summary page (sidebar, Admin only, like Purchase). Read only. Per supplier: orders, pending orders, amount bought (received orders only), amount returned (supplier returns), net, and last delivery date. Totals at the top.
- Backup: not added, because a daily backup (scripts/backup_db.bat) and a restore script already exist (v82).
- Supplier payments are not recorded anywhere yet, so the page does not show what is still owed to a supplier.
- Build marker set to v86.47.

## v86.48 - Supplier payments
- New table supplier_payments (created at startup if missing): supplier, amount, date, method, note, user.
- Supplier Summary page now has a payment form (Admin only) and shows Paid and Owed (Owed = Bought - Returned - Paid) for each supplier, plus the last 30 payments.
- Payment rules: supplier must exist, amount above 0, date valid and not in the future. Each payment is written to the audit log.
- A payment only records money. It does not change stock or purchase orders.
- Build marker set to v86.48.

## v86.49 - Owner Summary (phone friendly)
- New Owner Summary page (sidebar, Admin only). Read only. Cards: today's sale and bills, low stock count (link to Medicines), expiry in next 90 days, supplier amount still owed, pending purchase orders, and customer dues (link to Customer Dues).
- Two-column layout on phones.
- Build marker set to v86.49.

## v86.50 - Activity Log filter
- New Activity Log page (sidebar, Admin only). Read only, shows the latest 200 entries from audit_log.
- Filters: user (partial name), action (pick from list), item type, and from/to date.
- Dates are checked; user text is escaped so % and _ are searched as plain text.
- Note: an older audit page was removed in step 11O. This is a new, smaller page that reads the same table. Nothing was written to audit_log by this change.
- Build marker set to v86.50.

## v86.51 - Voice search on medicine search boxes
- Mic button next to the search box on Medicines and on the section pages (Syrups, Creams, Drip, Other, Overview).
- Speak a name, the words go into the box and the live filter runs.
- Language is English (en-IN), so English medicine names work best. Urdu script is not matched to the English names in the database.
- Works only where the browser allows the microphone: Chrome on the shop PC (localhost) or an https address. On a phone over plain http the button is hidden. Nothing else changes.
- Build marker set to v86.51.

## v86.52 - Clear message when the database is down
- guarded() now recognises MySQL connection errors (2002, 2003, 2006, 2013).
- Page visit: shows a short message (MySQL running? try again, nothing was saved) with status 503.
- Form save: flashes the same message and sends the user back to the page. Nothing is written.
- API calls: JSON with code DB-DOWN and status 503.
- Other errors keep the old ERR-id message.
- Build marker set to v86.52.

## v86.53 - Medicines page shows only the Medicines section
- The Medicines list and its stat cards (total, in stock, low, empty) now count only the medicines section: tablets, capsules, powders, sachets, suppositories, inhalers, and items with no form.
- Syrups, creams, drip/injection and bandage items stay on their own section pages only.
- Barcode duplicate check still looks at all items, so a barcode used in any section is still warned.
- Build marker set to v86.53.

## v86.54 - Duplicate error (same name and strength)
- A medicine with the same name AND the same strength as a live medicine can no longer be saved. It shows a red error: "Duplicate: '<name> <strength>' pehle se maujood hai... Naya save nahi hua."
- Checked on: Medicines add, Medicines edit, section Add item, section Edit.
- Same name with a different strength is allowed (for example Panadol 500 and Panadol 120).
- Blank strength counts as blank, so two items with no strength and the same name are a duplicate.
- Deleted (hidden) items are ignored, so a name can be reused after deleting.
- Before: Medicines add/edit gave a yellow warning on name only, and section Add gave a warning. Now it is an error and nothing is saved.
- Build marker set to v86.54.

## v86.55 - Mic button look and cache fix
- The mic button showed as a plain bordered box because the browser kept an old copy of medicine-look.css. The stylesheet link now uses ?v=2, so browsers load the new file.
- Mic button is now a round, light teal button placed left of the clear (×) button. Turns red while listening.
- Build marker set to v86.55.

## v86.56 - Actions column always visible
- On Medicines and section tables the Actions column is now sticky on the right edge. When the table is wider than the screen, the buttons (cart, edit, receive, history, delete) stay in view and Delete is no longer cut off.
- Stylesheet version set to ?v=3 so browsers load the change.
- Build marker set to v86.56.

## v86.57 - Shop log review (attachment from the shop PC)
Checked the log from the shop (Windows paths, user "ahmed"). Findings:
- /drip errors (Unknown column sale_id, customers.contact): from the old v69 copy. Current code already fixes them: /drip redirects to the Drip section, and ensure_drip_table adds sale_id before every sale. Nothing to change.
- products edit "batches" error and receive "dosage_form" error: from v69. The current edit route sets batches on GET. The receive routes now read dosage_form with .get(), so a missing column cannot crash them.
- "barcode unique index not added (duplicate barcodes in old data)": the shop database still has duplicate barcodes (warning on every start). Data Quality now lists "Same barcode on two items" so they can be fixed. The unique index is only added after the duplicates are fixed.
- Build marker set to v86.57.

## v86.58 - Bigger, clearer search box on Medicines and all section pages
- Search box is wider (up to 580px), taller (46px), with a larger font and a soft border and shadow. The placeholder text is no longer cut off.
- Teal focus ring when typing. Mic and clear buttons are placed inside the box, on the right.
- Barcode scan box on section pages has its own style (scan-box) and no extra left space.
- Phone layout keeps full width.
- Only Medicines and section pages load this stylesheet, so other pages are not changed.
- Stylesheet version set to ?v=4. Build marker set to v86.58.

## v86.59 - Dashboard: profit and loss for every section
- New card on the dashboard: "Profit aur Loss (sab sections)". For Medicines, Syrups, Creams, Drip and Other: sold count, sale, cost and profit for today, plus sale and profit for this month. A total row is at the bottom.
- Loss (cost more than sale) is shown in red with a Loss badge.
- Uses the same formula as the Reports section page (sale minus batch purchase price, returns taken out).
- Expenses are not in this yet (expense khata comes later), so the profit here is before expenses.
- A failure in this card is logged and the dashboard still opens.
- Build marker set to v86.59.

## v86.60 - Cash drawer (first version)
- New Cash Drawer page (sidebar, for Admin, Pharmacist and Cashier).
  - Open the drawer with the opening cash. Only one drawer can be open at a time.
  - Cash in and cash out with a reason (for example: tea, electricity, udhaar wapas).
  - Live expected cash = opening + cash sales today − cash refunds + cash in − cash out.
  - Close: count the cash. The page shows Short or Extra at once. Each close is saved with who did it.
  - History of the last 14 sessions with the shortage.
- Cash sales are counted from the sales table (payment method Cash). The sale code is not changed.
- Tables cash_sessions and cash_movements are created at startup if missing.
- Pure maths (expected and shortage) is in pharmacy/services/cash_drawer.py and is tested.
- Not in this version: udhaar repaid in cash is not counted automatically (enter it as Cash in with a reason). Card and Online are not counted in the drawer (they are not cash).
- Build marker set to v86.60.

## v86.61 - Cash drawer udhaar, Expenses khata, dashboard paise ka hisaab
- Cash drawer ab cash-in `sale_payments` (method Cash) se count karta hai. Normal cash sale aur udhaar wapsi dono wahin likhi jati hain, is liye udhaar cash mein wapas ayega to drawer mein khud count hoga. Purana `sales.paid_amount` wala term hata diya (double count nahi hoga).
- Naya `expenses` table (startup par ban jata hai). Naya page `/expenses` (Admin, Pharmacist): Bijli, Salary, Chai aur pani, Kiraya, Transport, Maintenance, Other. Kharcha sirf add hota hai (edit/delete nahi). Mahine ka total aur category breakdown.
- Agar kharcha cash mein diya gaya aur drawer khula hai, to drawer mein cash out bhi likha jata hai.
- Dashboard par "Paise ka hisaab" card: Cash in hand (drawer khula ho to expected, warna "Drawer band"), Total udhaar (sab customers), kharcha aaj/mahina, aur kharcha ke baad net profit aaj/mahina.
- Sidebar mein Expenses link. Build marker v86.61.
- Tests: test_expenses.py (21 checks), test_cash_drawer.py updated (20 checks).

## v86.62 - Offline bill ID (stage 1), Data Quality "No category" list
- sales.client_uuid column aur unique key (startup par khud ban jata hai). Ek bill ki ID ek hi baar save hoti hai. Dobara bheji gayi same ID par wahi bill wapas milta hai, stock dobara nahi katta.
- Data Quality: "No category" ke neeche link. Medicines page `?issue=nocat` par sirf bina category wali items dikhata hai.
- Build marker v86.62. Tests: test_offline_bill_id.py (6 checks).
- Offline mode ke stage 2 se 4 abhi baqi hain (POS queue, browser cache, sync).

## v86.63 - Offline bill queue on the sale page (stage 2)
- Sale page (/sales/new): agar server tak pohanch na ho (network drop ya 12 second timeout), bill browser ke IndexedDB mein save hota hai, apni bill ID ke sath. Form saaf ho jata hai aur status dikhta hai.
- "Sync karein" button, aur internet wapas aane par khud sync. Bill dobara jane par same ID ki wajah se double save nahi hota. Sync ke waqt CSRF token current session ka lagta hai.
- Server ki galti (stock, bad input) par bill queue mein rehta hai aur dikhta hai. Non-JSON jawab (login page) ko fail samjha jata hai.
- Stage 2 ki hadd: sale page pehle se khuli honi chahiye. Agar page reload ho aur server band ho to page hi nahi khulega. Ye stage 3 (page aur medicine list ka cache) mein hoga.
- Build v86.63. Tests: test_offline_sale_queue.py (14 checks), suite 1860 pass.

## v86.64 - English error messages, offline sale page cache (stage 3)
- Sab error, warning, success aur status messages ab English mein hain (flash messages, API errors, DB-down page, cash drawer, expenses, offline queue, voice search, chatbot errors). UI labels Roman Urdu mein hi hain.
- Stage 3: sale page (/sales/new) har kamyab online visit par browser mein save hota hai. Net jane par wahi copy khulti hai, lekin sirf 24 ghante tak. Is ke baad page band ho jata hai aur message aata hai ke net se connect karein.
- Sync se pehle CSRF token refresh hota hai, taake purani saved page se bhi bills sync ho jayen. Session expire ho to bills queue mein rehte hain aur message aata hai ke dobara login karein.
- Service worker cache v5. Medicine list ka alag offline cache abhi nahi hai (sale page ke andar ki medicine list hi use hoti hai).
- Build v86.64. Tests: suite 1867 pass, 0 fail.

## v86.65 - No Roman Urdu in user-visible text
- Templates, JavaScript messages, flash and API messages, receipts, reminder text and expense categories ab English mein hain. Code comments, CHANGELOG files aur chatbot ke typed command keywords (jaise "ka shelf", "naya customer") jaise the waise hain taake purane commands chalte rahen.
- Expense categories: Electricity, Salary, Tea and water, Rent, Transport, Maintenance, Other.
- Build v86.65.

## v86.66 - Offline sync: stock short handling, status messages, browser-tested queue
- Offline bill sync par stock kam ho to bill reject nahi hota. Jo quantity batch mein nahi hai wo batch NULL ke saath save hoti hai, aur medicine stock minus mein chala jata hai. Data Quality mein naya check "Negative stock" ye items dikhata hai. Normal sale par ab bhi stock se zyada bill nahi banta.
- Status messages ab sahi rehte hain: "Network not available ... (ID ...)", "Sync: N bill(s) saved", aur refused bills ke liye "need review". Pehle queue count inhe overwrite kar deta tha.
- Session expire ho to "Session expired" message aata hai aur bill queue mein rehta hai.
- Browser test (Chromium, harness page, server replies simulated): 12 checks pass. Service worker ka 24-hour cache browser test mein nahi hua.
- Build v86.66.

## v86.67 - Dashboard medicine card counts the Medicines section only
- "Total medicines" card ab sirf Medicines section (tablets, capsules, powders) ka count dikhata hai. Pehle ye sab sections ka mila-jula total tha.
- Card ke neeche Syrups, Creams, Drip & Injection aur Bandages & Other ke alag counts dikhte hain.
- Build v86.67. Tests: suite 1873 pass, 0 fail.

## v86.68 - Dashboard low stock counts the Medicines section only
- Dashboard ka "Low stock items" card aur "medicines need restocking" insight ab sirf Medicines section dekhte hain, Medicines page ke saath match karte hain.
- Build v86.68. Tests: suite 1875 pass, 0 fail.

## v86.69 - Dashboard low stock for every section, separately
- "Low stock items" card ab sab sections ka total dikhata hai, aur neeche har section ka alag count (Medicines, Syrups, Creams, Drip, Bandages & Other).
- Restocking insight mein bhi section ke hisab se counts dikhte hain.
- Low stock list mein ab "Section" column hai.
- Build v86.69. Tests: suite 1876 pass, 0 fail.

## v86.70 - Dashboard expiring batches for every section, separately
- "Expiring soon" card ab sab sections ke batches dikhata hai (90 din ke andar), har batch ke saath section ka naam.
- Card mein har section ka alag count, aur insight mein total batches.
- Build v86.70. Tests: suite pass, 0 fail.

## v86.71: sale screen item search

- Sale screen: the item dropdown in each row is replaced by a search. Type a name, part of a name, dosage form, section name or barcode. A live list opens under the search box (up to 12 items, best matches first, with section, price and stock).
- Keys: Up/Down to move, Enter to add, Esc to close, `3*pan` adds 3 pieces. A full barcode scan is always taken as a barcode first.
- After picking from the list, the cursor goes to the quantity box. Type the number, press Enter, and the cursor returns to the search box. No mouse needed.
- Clicking a filled row's item lets you pick a different item for that row. If the new item is already on another row, the quantities are merged (no duplicate rows).
- Out-of-stock items are shown greyed and cannot be added.
- F3 now puts the cursor in the search box.
- Form posts are unchanged (the hidden select still sends medicine_id[]), so the server side and offline sync are not affected.
- Tests: tests/test_sale_search_v8671.py (static). Browser check done in Chromium with 20 steps (typing, arrows, Enter/Esc, barcode, multiplier, mouse click, row change, merge, totals, form data).

## v86.72: sale screen fixes

- Esc now cancels a pending row change, so a later Enter adds a new item instead of replacing the row.
- The row change message names the row number.
- Typing a letter inside a quantity box starts the next search (no need to click back to the search box).
- Items with price 0 show "Price not set" in the list, and the add message warns to set the price before billing.
- Browser checks: 28 steps in Chromium, all pass. Tests: 1887 pass, 0 fail.

## v86.73: search keeps the cursor, sticky search bar

- After a pick (Enter or click) the item is added at quantity 1 and the cursor stays in the search box. The next item can be typed at once. Quantity is changed in the row, or by typing `3*name`.
- The search bar sticks to the top while the bill table scrolls, so the search is always visible.
- A live "Items" count and "Total" are shown under the search bar.
- The row that changed is highlighted for a moment.
- Tests: 1887 pass, 0 fail. Chromium checks pass (19 steps).

## v86.74: quantity controls

- Each row's quantity has a big minus and plus button (44px, easy on a phone). Minus never goes below 1. Plus stops at the stock on hand, with a message.
- In an empty search box, `+` and `-` change the quantity of the last added item. Example: type "pan", Enter, then `+` makes it 2.
- Clicking a quantity box selects the number, so typing replaces it.
- Picking an item already on the bill adds one more to that row.
- Tests: 1888+ pass. Chromium checks: 13 quantity steps plus the search checks, all pass.

## v86.75: product picker

- Multi-select: tick "Select several, then add together". Click cards to choose them (they are highlighted), then press "Add all to bill". Clear empties the choice.
- Badge on each card (x2 etc.) shows how many of that item are already on the bill.
- Enter in the picker search adds the first matching item.
- Picker cards are smaller, and the picker scrolls in its own box, so the search bar and bill stay on screen.
- Quantity box is wider, so the number is always visible.
- Tests: all pass. Chromium checks: 14 picker steps plus earlier checks.

## v86.76: dashboard rebuilt per product section

- Fixed: section names showed "<built-in method items of dict>" on the dashboard. The template now reads the values by key.
- Section records table: one row per section (items, in stock, low, no stock, expiring 90 days, sold/sales/profit/purchase today, sales/profit/purchase this month, customers this month).
- One card per section: stock figures, month sales and purchase bars (animated), profit, customers, best sellers (30 days), low stock items, batches expiring within 90 days.
- Profit and loss per section for this month, with a total and net profit after expenses (today and month).
- Recent sales list removed.
- Quick actions: create sale, add medicine, new customer, receive stock (purchase), expenses, reports (Admin), AI assistant.
- Drip & Injection records summary kept at the bottom of the page.
- Day restarts at 12:00 AM on the shop PC clock (all "today" figures use the shop date). No manual reset.
- 7-day chart of sales against purchases (animated bars), and the existing sales chart with a screen-reader table.
- Service: pharmacy/services/dashboard_records.py. Tests: tests/test_dashboard_records.py (13 checks). Suite: 1902 pass, 0 fail.
- Not checked against a live MySQL here (no MySQL in the test environment). Check the dashboard on the shop PC.

## v86.77: expiry window, customers, price-0 warning, animated top sellers

- Expiry window is 90 days everywhere now: dashboard, Product sections page, Products hub, Drip & Injection records. (It was 60 on some pages.)
- Customers per section: this month and all time (shown on each section card and on the dashboard header card).
- Medicines with price 0 or no price are counted per section, shown on the dashboard, and link to Data Quality (check "No price or zero price"). Fix the price in Medicines > Edit.
- Best sellers (30 days) are animated bars per section, with units and revenue.
- Drip & Injection block: fixed "<built-in method ...>" text (the item count now reads by key).
- Tests: 1904 pass, 0 fail.

## v86.78: dashboard look restored

- Welcome hero is back (pharmacy picture, name, date, time). The greeting changes with the time: Good morning (before 12), Good afternoon (before 5 PM), Good evening.
- Four classic KPI tiles under the hero: total items (with the split per section), total customers, today's sales, purchase orders. Numbers count up on load.
- Cards slide in when they reach the screen, from alternate sides. Charts and bars animate. The Animation switch still turns motion off.
- Fixed: "Total items" showed "<built-in method ...>" (the value is read by key now).
- Tests: 1904 pass, 0 fail.

## v87.00 - Stock count screen

English: New "Stock Count" page in the sidebar (Admin and Pharmacist). Start a count (one at a time), enter the counted quantity per medicine, search by name or barcode, filter to not-counted or changed rows, save in parts, submit, then an Admin approves. Approval sets stock to the counted quantity, writes one stock adjustment and one audit row per changed medicine, and is refused if stock changed during the count. A submitted count can be sent back to counting. Batches are not changed by approval (use batch reconcile after). Tests: tests/test_stock_count.py (28), tests/test_stock_count_routes.py (19).

Roman Urdu: Sidebar mein "Stock Count" page. Admin aur Pharmacist count shuru kar sakte hain, har dawa ki counted quantity likh kar save karein, phir submit karein. Admin approve karega to stock counted quantity par set ho jayega. Agar count ke dauran kisi dawa ka stock badla (jaise sale), to approval ruk jayega aur count dobara karna hoga. Batches approval se nahi badalte.

## v87.01 - Cold chain log screen

English: New "Cold Chain Log" page in the sidebar, open to Admin, Pharmacist and Cashier. Record a fridge or store temperature with a place name, value and optional note. Normal range is 2 to 8 C. A reading outside the range is still saved and shown in red with a warning. Page shows the latest reading per place, today's count of readings and out-of-range readings, and the last 60 readings. There is no delete: readings are a permanent record. Tests: tests/test_cold_chain.py (26).

Roman Urdu: Sidebar mein "Cold Chain Log" page. Fridge ka temperature likh kar save karein (normal 2 se 8 C). Range se bahar ka reading bhi save hota hai, lekin laal dikhta hai aur warning aati hai. Reading delete nahi hoti.

## v87.02 - Controlled drug register viewer and export

English: New "Controlled Register" page in the sidebar, open to Admin and Pharmacist. It shows every scheduled-medicine sale entry (written automatically by the sale), with date range (default last 30 days, max one year), medicine search and schedule filter, totals per medicine, and the newest 500 entries. Export to CSV asks the user to type their own password, and each export is written to the activity log. The page never edits or deletes register entries. Compliance format is still to be confirmed with the drug authority. Tests: tests/test_controlled_register_screen.py (23).

Roman Urdu: Sidebar mein "Controlled Register" page. Scheduled dawaiyon ki har sale ki entry yahan dikhti hai. Date range, dawa ka naam aur schedule se filter karein. CSV export ke liye apna password likhna hoga. Entries edit ya delete nahi hoti. Register ka sahi format drug authority se confirm karna baaqi hai.

## v87.03 - Cash drawer lock

English: Cash can only be taken or paid out while the cash drawer is open. Applies to: live cash sales (sale screen and POS API), receiving a cash payment on an old bill (udhaar), and cash expenses. When the drawer is closed these are refused before anything is written, with the message "The cash drawer is closed. Open the drawer ..., or use another payment method." Card, Online and zero amounts are not affected. Offline bills that sync later are not re-checked (they are saved on the device and the drawer may already be closed). Tests: tests/test_cash_lock.py (19). Existing sales and POS test fakes now report an open drawer.

Roman Urdu: Drawer band ho to cash sale, udhaar ki cash wapsi aur cash kharch save nahi hote. Message aata hai ke pehle drawer kholen. Card aur Online par koi rok nahi. Offline bills sync ke waqt dobara check nahi hote.

## v87.04 - Profit margin per item

English: New read-only "Profit Margin" page (Admin and Pharmacist). Margin = sale price minus cost, with percent. Cost is the purchase price of the last received batch, falling back to the item's cost price. Statuses: sold below cost, no sale price, no cost, low margin (under 10%), healthy. Worst items are listed first, with filters and search. Tests: tests/test_margins.py (23).

Roman Urdu: Sidebar mein "Profit Margin" page. Har dawa ka margin (sale price minus cost) aur percent dikhta hai. Cost aakhri batch ki purchase price se aati hai. Sabse kharab items (cost se neeche bechi jane wali, price ya cost missing) sab se upar hote hain. 10% se kam margin "Low" dikhta hai.

## v87.05 - Purchase drafts (auto order draft)

English: New "Purchase Drafts" page (Admin and Pharmacist). "Create drafts" turns the current purchase suggestions into one draft per supplier (supplier taken from the last purchase order of each item; items with no history go to one draft with no supplier). Items already on an open draft are not added again. Quantities can be changed; 0 removes a line. Export CSV, mark as sent, or cancel. Drafts never change stock: receiving still happens on the Purchase page. Migration 008 adds purchase_drafts and purchase_draft_lines. Suggestion rows now also carry medicine id and cost. Tests: tests/test_purchase_drafts.py (32).

Roman Urdu: Sidebar mein "Purchase Drafts". Kam stock ki suggestions se supplier ke hisaab se draft order banta hai. Quantity badal sakte hain, 0 karne par item hat jata hai. CSV export, "sent" ya cancel ka option hai. Draft se stock nahi badhta; maal aane par Purchase page par receive karein.

## v87.06 - Photo reader readiness (Tesseract, offline)

English: The prescription photo page now checks Tesseract once a minute. It shows a green banner when Tesseract and the English language data are found (with version), or an amber banner with the reason and the install guide (TESSERACT_INSTALL_ROMAN_URDU.md) when not. Decision: OCR stays on the shop PC (offline); no cloud AI is used. Tests: tests/test_ocr_readiness.py (11).

Roman Urdu: Prescription photo page par ab banner aata hai. Tesseract mil jaye to hara message, nahi to peela message aur install guide ka hawala. Photo ka data PC se bahar nahi jata.

## v87.07 - Drug interaction pairs (warnings only)

English: New "Drug Interactions" page (Admin and Pharmacist add pairs; only Admin deletes). Staff enter pairs of medicines with severity (minor, moderate, major) and an optional note. After a sale is saved, any listed pair in the bill shows a warning. Nothing is blocked. The page states that the list is not a complete drug database and that an unlisted pair is not confirmed safe. Migration 009 adds drug_interactions (one row per pair). Tests: tests/test_interactions.py (27).

Roman Urdu: Sidebar mein "Drug Interactions". Staff dawaiyon ke jodey aur severity daal sakti hai. Sale save hone ke baad agar bill mein koi listed jora ho to warning aati hai. Sale block nahi hoti. Yeh list complete drug database nahi hai.

## v87.08 - Controlled schedule field on the product edit page

English: The product edit page now has a "Controlled schedule" field (blank = not controlled). Saving writes it to medicines.schedule and to the activity log. The page warns that a schedule makes every sale of the medicine require a prescription and be written to the Controlled Register. The shop types the schedule name its drug authority uses; no categories are invented. This closes the gap where the register could never fill from the app. Tests: tests/test_schedule_field.py (10).

Roman Urdu: Product edit page par "Controlled schedule" ka khana hai. Khali ho to dawa controlled nahi. Schedule lagane par us dawa ki har sale ke saath prescription zaroori ho jati hai aur entry Controlled Register mein jati hai.

## v87.09 - Software license key (warning only)

English: Admin "License" page to paste a key. Key is checked with HMAC-SHA256 using LICENSE_SECRET from .env. States: valid, expiring (14 days), expired, wrong PC, invalid, missing, no secret. A banner shows on every page unless the license is valid. Billing is NEVER blocked. Bad keys are not saved; expired keys are saved so the banner reflects them. Machine id shown for keys tied to one PC. Key tool: scripts/make_license.py (run on the owner's computer). Limit: checking needs the same secret as the shop, so this stops casual copying only. Tests: tests/test_license.py (32).

Roman Urdu: Admin ke "License" page par key daali ja sakti hai. Expire ya galat key par har page par warning banner aata hai, lekin billing kabhi band nahi hoti. Key banane ka tool scripts/make_license.py hai, jo malik ke computer par chalta hai.

## v87.10 - Customer portal (read only, phone + shop-set PIN)

English: Staff (Admin, Pharmacist) set a 4 to 6 digit PIN per customer on "Customer Portal" (sidebar); the PIN is stored as a bcrypt hash, never shown again, and never written to the log. Customers open /portal on their phone, log in with phone and PIN, and see only their own last 20 bills with items, paid, returned and amount due. Five wrong PINs lock the account for 15 minutes. Wrong phone and wrong PIN give the same message. Portal session is separate from staff login. The portal writes nothing. Migration 010 adds customer_portal_accounts. Internet hosting needs HTTPS and is a separate step. Tests: tests/test_customer_portal.py (40).

Roman Urdu: Staff customer ke liye PIN set karti hai (Customer Portal page). Customer phone par /portal khol kar apne bills dekh sakta hai. Paanch ghalat PIN par 15 minute lock. Sirf read karna hai.

## v87.11 - Multi-branch summary (counts only)

English: New read-only API endpoint /api/v1/branch/summary (token, Admin or Pharmacist) returning counts only: today and month sales and bills, out-of-stock, low-stock, batches expiring in 90 days, customers with dues. New "Branch Summary" page (Admin) stores the other branch's name, address and API token, and shows both branches side by side on "Check now". Addresses must be https://, plain http:// only on LAN or localhost. The token is never logged; an empty token box keeps the saved token. Hosting the other branch on the internet is a separate step. Tests: tests/test_branch_summary.py (26).

Roman Urdu: Doosri branch ka summary (sirf numbers) ek page par. Sirf Admin dekh aur set kar sakta hai. Internet address https:// hona chahiye. Medicine ya patient ke naam share nahi hote.

## v87.12 - Seasonal purchase forecast (rules, suggest only)

English: New "Purchase Forecast" page (Admin and Pharmacist). For each medicine it compares the last 30 days with the same 30 days last year, takes the higher daily rate, and suggests how much to order for the next 30 days (never below the reorder level, minus stock now). Flags a season when last year's window is at least 1.5x the recent one and at least 5 units. Read-only: items go to Purchase Drafts after review. Tests: tests/test_purchase_forecast.py (18).

Roman Urdu: Sidebar mein "Purchase Forecast". Pichle saal isi mausam ki sale dekh kar agle 30 din ka andaza deta hai. Sirf suggestion hai, order khud nahi hota.

## v87.13 - Sidebar restructure, Finance and Sales & Billing hubs

English: Sidebar regrouped into Main, Inventory (was "Product Overview"; now holds Batches & Expiry, Expired & Alerts, Cold Chain Log, Stock Count, Categories, Controlled Register), Suppliers (Supplier Returns merged in, plus Purchase Drafts, Forecast, Summary), Sales & Billing, Finance (hub page: Cash Drawer, Expenses, Daily Closing, Customer Dues, Profit Margin, Owner Summary, Reports), Reports, AI Assistant, Settings (Admin: Users, Activity Log, Data Quality, Records Clear), Account. Customer Portal, Branch Summary and License are visible to Admin and Pharmacist. Two new hub pages (/finance, /sales-billing) list their links as cards, filtered by role. No data or permission rules changed for the pages themselves. Tests: tests/test_hubs.py (9); four older sidebar checks now accept the hub pages.

Roman Urdu: Sidebar ab sections mein saaf hai. "Product Overview" ka naam "Inventory" hai. Finance aur Sales & Billing ke apne hub pages hain jahan saare links cards ki shakal mein hain. Supplier Returns Suppliers ke andar aa gaya. Kisi page ka access nahi badla.

## v87.14 - Motion layer and soft sound

English: New static/css/motion.css and static/js/motion.js, loaded on every page. Page content rises in gently on load. Sidebar items glide on hover, and the active item gets a slim accent rail. Cards lift slightly on hover, buttons press in, and sidebar links fade before moving to the next page. Sound is off by default. A "Sound" button in the top bar turns it on for this device only (stored in this browser). When on, a soft synthesized chime plays on sidebar navigation, when sound is first turned on, and on success messages. No audio files. Reduced-motion users get no movement. POS and sale screens get no new motion. Tests: tests/test_motion.py (9).

Roman Urdu: Sidebar aur pages par naram animation aur har page ki entry mein halka slide. Sound by default band hai. Top bar mein "Sound" button se is device par on karein. Sales screen par koi animation ya sound naya nahi laga.

## v87.15 - Motion toned down

English: Motion made calmer. Page entry moves 4px (was 8px) and is shorter. Sidebar hover uses a soft background instead of sliding. Card lift removed (shadow only). Logo shimmer removed. Button press is 1.5% (was 3%). Alerts settle faster. Tests: tests/test_motion.py (9).

Roman Urdu: Animation ab halki hai. Sidebar par slide nahi, sirf halka rang. Card uthta nahi, sirf shadow. Logo ki chamak band.

## v87.16 - Sidebar cut to nine entries, group hub pages

English: Sidebar now has nine entries: Dashboard, Medicines, Inventory, Sales & Billing, Purchasing, Finance, AI Assistant, Admin, and Account (My Profile, Logout). Each group opens a hub page (/medicines-hub, /inventory-hub, /sales-billing, /purchasing-hub, /finance, /admin-hub) that lists its pages as cards, filtered by role. No page moved or changed its permissions; only the links changed. Admin hub shows Customer Portal, Branch Summary and License to Pharmacist too. Tests: tests/test_hubs.py (10); older sidebar checks now read the hub list.

Roman Urdu: Sidebar ab 9 entries mein hai. Har group ka apna hub page hai jahan uske pages cards mein hain. Koi page ka access nahi badla.

## v87.17 - Animation and sound panel

English: The top-bar button "Animation & sound" opens a panel with Speed (0.5x to 2x), Strength of motion (0 to 2), Sound volume (0 to 100%), Sound on/off, a Test sound button and Reset. Settings are saved per device in this browser. Speed and strength apply live to all page motion. Motion uses transform and opacity only. Tests: tests/test_motion.py (11).

Roman Urdu: Top bar mein "Animation & sound" button se panel khulta hai. Is mein speed, strength, volume aur sound on/off hain. Ye setting is device par save hoti hai.

## v87.18 - Pharmacy Catalog name, dashboard layout, Owner Summary slides

English: Sidebar and hub for the medicine group are named "Pharmacy Catalog". Dashboard gets a new layout stylesheet (static/css/dashboard-pro.css): KPI tiles in a responsive grid with accent lines and hover, even card grid, pill quick actions, bar grow animation, and staggered card entry. All data and element hooks are unchanged. Owner Summary is now five full-screen slides (sales, stock, expiry, suppliers, customer credit) with dots and arrow keys; each slide has a link to its page. Tests: tests/test_owner_home.py updated for the slide layout.

Roman Urdu: Medicines ka naam "Pharmacy Catalog" hai. Dashboard ka layout naya hai, numbers aur cards ka animation hai. Owner Summary ab slides mein hai, arrow keys aur dots se aage peeche.

## v87.19 - Cloud database check script

English: New scripts/check_cloud_db.py. It reads the CLOUD_DB_* keys from .env, connects read only, and reports OK, the server version, and whether TLS is on. It never prints the password and gives a plain message for login, database name, and network errors. .env.example lists the CLOUD_DB_* keys (empty by default). Nothing in the app uses them yet; Phase 1 of offline mode comes next.

Roman Urdu: Cloud database ka connection check karne ka script. Password sirf .env mein, chat mein nahi.
