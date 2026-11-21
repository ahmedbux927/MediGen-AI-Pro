# MediGen v85 - Drip & Injection sell, 500 error fix

## Fixed
- /drip gave error 500 on a database made by v77: the table had no sale_id column and customer_id was required.
  ensure_drip_table() now adds the missing column and makes customer_id optional (_upgrade_table). Runs once per start.
  This also fixes sales with an injection line, which write to the same table.

## New
- Drip & Injection page: "Sell a drip or injection" card at the top. Choose medicine, quantity, patient (optional, shows phone), then "Open sale and print".
  It opens the POS with the medicine and quantity already filled. Complete the sale, the drip record is saved automatically and the receipt prints.
- Barcode scan in POS still adds items and lowers stock at sale time (unchanged). Works for every product (medicines, bandages, packets, etc.).
- Sidebar keeps "Drip & Injection".

## Files
- pharmacy/services/drip_record.py: _upgrade_table, _column.
- pharmacy/routes/sales.py: new_sale accepts ?med=&qty=&customer= (prefill).
- pharmacy/routes/drip.py: sell list (stock > 0), patient phone.
- templates/drip.html: Sell card, manual form kept as fallback, sale number links to invoice.
- tests/test_drip_record.py: 38 checks. tests/frontend_manifest.json regenerated.

## Tests
- python tests/run_all.py: 1539 passed, 0 failed (live MySQL not run here).

## Check on shop PC
- Open /drip: no 500 error.
- Sell 1 injection to a patient: receipt prints, Drip & Injection list shows the row with "sale #".
- Run python tests\run_all.py --live with TEST_DB_* set.
