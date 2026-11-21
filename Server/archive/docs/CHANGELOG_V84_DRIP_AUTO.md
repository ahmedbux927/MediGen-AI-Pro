# MediGen v84 - Quick sell, drip and injection automatic

## Fixes
- /drip 500 error ("Unknown column d.sale_id"): a database made by v77 has no sale_id column. v84 adds it on start (and makes customer_id optional). Run v84 from its own folder; the v69 folder still has the old code.

## What changed
- Drip & Injection page is now a Quick sell page: all in-stock products (bandage packets and others too), with search and a Sell button. Drip and injection items show a DRIP / INJ tag.
- Barcode: type or scan the barcode in the search box and press Enter. If it matches a product in stock, the sale opens with that product added (qty 1).
- Drip and injection lines are recorded automatically when any sale is saved (counter or POS), with the sale number, patient (optional, walk-in allowed), and stock reduced.
- Manual record form is a collapsed fallback.
- POS and medicine list show the dosage form.

## Tests
- python tests/run_all.py: all passed (see last run).

## Quick sell additions
- Patient picker at the top of the Quick sell card (optional). Type a name or phone to filter the list; the first match is picked.
- Quantity box per product (1 to 50, max stock); Sell opens the sale with that quantity.

## Prescription OCR (Tesseract) setting
- .env: TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe (full path). Used first if the file exists.
- Without it, the app still checks PATH and the default Windows install folder. If none is found, the review page asks you to type medicines (no error).
- Install: Tesseract for Windows (UB Mannheim build), tick English during setup. Then set TESSERACT_CMD in .env and restart the app.

## Remember me (diagnostics)
- Code review found no defect that explains "Remember me not working" without a real run. Added log lines to logs\medigen.log:
  - "remember-me: cookie set for user N" when the box is ticked and login succeeds.
  - "remember-me: logged user N back in from the cookie" on reopen.
  - "remember-me: cookie present but no active token" if the cookie no longer matches (expired, logged out, or user inactive).
  - "remember-me: user N is outside the access hours" for cashier time windows.
- If the cookie-set line is missing, the browser is not getting the cookie. Check the address used (127.0.0.1 and 192.168.x.x are different sites).

## Drip page fix
- /drip 500 error "Unknown column 'contact'": the customers column is contact_number. Drip page now uses it (query and patient list, with name/phone search).

## Drip page cleanup
- Removed the "Add manually (rare)" form. Drip and injection sales are recorded automatically, so no separate form is needed. The /drip/add route still exists.
- Patient box shows "No patient matches. Walk-in will be used." when the typed name or phone finds nobody.
- Why the old manual Medicine list showed only "Choose medicine": no stock item had Dosage Form set to Injection or Drip / IV fluid. Set it in Medicines > Edit.

## Route on the sale screen (v85 step)
- When a drip or injection medicine is in a row, a Route select appears: Not set (default), IV drip, IV injection, IM injection, SC injection.
- The chosen route is saved in the automatic drip record. Other rows are unchanged.
- POS / app checkout (services/pos.py) still saves "Not set" for now.

## Drip and injection list (v85)
- Drip & Injection is in the Main section, under Medicines (was below Prescriptions).
- Drip page is one column; the product table scrolls inside its card, so the Sell button stays visible.
- Load list: upload a CSV (generic_name, dosage_form required). Injection and Infusion / IV solution rows are imported; existing names are skipped. All or nothing.
  - tests/fixtures/drip_injection_list.csv (383 rows) loads 366 unique items (duplicate names are kept once).
  - Price, cost and stock are 0 after import. Set price in Medicines (Edit), add stock by Purchase.
- Add one item: name, strength, Injection or Drip / IV fluid.
- Remove: only if the item has no sales, batches, stock history or drip records. Otherwise a message says why.
- Quick sell lists all drip and injection items; items with no stock show "No stock" and a disabled Sell.
- Backend: services/drip_catalog.py (parse, import, remove check), routes /drip/import, /drip/item/add, /drip/item/<id>/remove. All writes are audited.

## Drip and injection records, stock and expiry (v85)
- Dashboard: Drip & Injection tile with items in stock, given today (units), low stock, batches expiring in 60 days, and expired units still in stock. A failing query cannot break the dashboard.
- Records page (/drip/records, Admin and Pharmacist): date range (default today, max one year), totals, records table with sale link, expiry table (expiring and expired batches), CSV download.
- Drip page links to the records page.
- Backend: services/drip_report.py (summary, expiring batches, records). Read-only.
