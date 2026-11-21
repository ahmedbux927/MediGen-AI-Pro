"""v77: drip and injection record. Rules, form reading, stock order, and wiring checks. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import drip_record as DR
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

ok(DR.is_drip_form('Injection') and DR.is_drip_form('Drip / IV fluid'), 'Injection and Drip / IV fluid are drip forms')
ok(DR.is_drip_form('injection 2ml') and DR.is_drip_form('IV infusion'), 'older text such as "injection 2ml" also counts')
ok(not DR.is_drip_form('Tablet') and not DR.is_drip_form('Syrup') and not DR.is_drip_form(None), 'tablets, syrups and empty forms are not drip forms')
ok(not DR.is_drip_form('Ivory cream'), 'a word that only starts with "iv" is not a drip form')

good = {'medicine_id': '5', 'customer_id': '2', 'route': 'IV drip', 'dose_text': '500 ml over 2 hours', 'quantity': '1', 'notes': ' '}
rec = DR.read_record(good)
ok(rec['medicine_id'] == 5 and rec['customer_id'] == 2 and rec['quantity'] == 1, 'a good form is read into numbers')
ok(rec['notes'] is None, 'blank notes are stored as NULL')
def bad(**change):
    try:
        DR.read_record(dict(good, **change)); return None
    except ValueError as e:
        return str(e)
ok(bad(medicine_id='') and 'medicine' in bad(medicine_id=''), 'no medicine is refused')
ok('patient' in bad(customer_id='x'), 'a patient id that is not a number is refused')
ok(DR.read_record(dict(good, customer_id=''))['customer_id'] is None, 'no patient means walk-in (allowed)')
ok('how it was given' in bad(route='Oral'), 'a route outside the list is refused')
ok('dose' in bad(dose_text='  '), 'an empty dose is refused')
ok('too long' in bad(dose_text='x' * 101), 'a long dose text is refused')
ok('whole number' in bad(quantity='1.5'), 'a fraction quantity is refused')
ok('between 1 and 50' in bad(quantity='0') and 'between 1 and 50' in bad(quantity='51'), 'quantity must be 1 to 50')
ok(DR.ROUTES == ['Not set', 'IV drip', 'IV injection', 'IM injection', 'SC injection'], 'the five routes are fixed, Not set is the automatic default')
ok(DR.AUTO_ROUTE == 'Not set', 'automatic sale rows use Not set as route')
ok('def auto_record_sale' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_record.py'), encoding='utf-8').read(), 'auto_record_sale exists')
sales_src = open(_os.path.join(ROOT, 'pharmacy', 'services', 'sales.py'), encoding='utf-8').read()
ok('DR.auto_record_sale(cur, sale_id, customer_id, user_id, lines, drip_routes)' in sales_src, 'save_sale records drip and injection lines automatically, with the chosen route')
ok(sales_src.index('DR.auto_record_sale') < sales_src.index('sale_payments'), 'drip record is written inside the same sale transaction')
ok("m.dosage_form" in open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read(), 'POS medicine list carries the dosage form')
ok('[{{ m.dosage_form }}]' in open(_os.path.join(ROOT, 'templates', 'new_sale.html'), encoding='utf-8').read(), 'POS option shows the dosage form')

lib_src = open(_os.path.join(ROOT, 'pharmacy', 'lib.py'), encoding='utf-8').read()
ok("'Drip / IV fluid'" in lib_src and "'Injection'" in lib_src, 'medicine dosage form list has the drip and injection choices')
ok("'dosage_form': dform or None" in lib_src and 'Please choose a valid dosage form' in lib_src, 'medicine form saves a checked dosage form')
route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'drip.py'), encoding='utf-8').read()
add = route.split('def drip_add')[1].split("@app.route('/drip/import'")[0]
ok(add.index('is_drip_form(med') < add.index('take_from_batches_fifo'), 'only drip or injection medicines are accepted, checked before stock is taken')
ok(add.index('if q > old') < add.index('take_from_batches_fifo'), 'stock is checked before it is taken')
ok("FOR UPDATE" in add and "'Given to patient'" in add, 'the medicine row is locked and the stock change is written to the adjustment history')
ok("drip.give" in add and 'INSERT INTO drip_injections' in add, 'the record and the audit line are written')
ok(add.count('mysql.connection.commit()') == 1 and 'mysql.connection.rollback()' in add, 'one commit at the end, rollback on any error')
ok(route.count('@role_required') == route.count("'Admin', 'Pharmacist'") and route.count('@role_required') >= 2, 'drip pages are for Admin and Pharmacist only')
ok('from . import drip' in open(_os.path.join(ROOT, 'pharmacy', 'routes', '__init__.py'), encoding='utf-8').read(), 'drip routes are registered')
base_html = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
def read_hubs_src():
    return open(_os.path.join(ROOT, 'pharmacy', 'routes', 'hubs.py'), encoding='utf-8').read()
ok("'key': 'drip'" in read_hubs_src() and "'key': 'syrups'" in read_hubs_src(), 'Medicines hub has a Drip & Injection link')
ok("redirect(url_for('products_section', key='drip'))" in route, 'the old drip page now opens the Drip & Injection section')
med_html = open(_os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8').read()
ok('Dosage Form' in med_html and 'm.dosage_form' in med_html, 'medicine add/edit have the dosage form field and the list shows it')

ok('_upgrade_table(cur)' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_record.py'), encoding='utf-8').read() and 'ADD COLUMN sale_id' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_record.py'), encoding='utf-8').read(), 'an older drip table gets sale_id added (fixes the 500 on /drip)')
ok('MODIFY customer_id INT NULL' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_record.py'), encoding='utf-8').read(), 'an older drip table gets optional patient')
routes_sales_src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
ok("request.args.get('med', type=int)" in routes_sales_src and "prefill_customer = request.args.get('customer', type=int)" in routes_sales_src, 'POS opens with the drip medicine, quantity and patient from the drip page')
ok('PS.section_for' in open(_os.path.join(ROOT, 'pharmacy', 'routes', 'products.py'), encoding='utf-8').read(), 'sell lists are per section (see test_product_sections)')

ok("code = (request.args.get('code')" in open(_os.path.join(ROOT, 'pharmacy', 'routes', 'products.py'), encoding='utf-8').read(), 'section page: scanned barcode adds the item to the sale cart')
ok("PS.section_for(r['dosage_form']) == key" in open(_os.path.join(ROOT, 'pharmacy', 'routes', 'products.py'), encoding='utf-8').read(), 'section page lists only products of that section')
ok("ALTER TABLE drip_injections ADD COLUMN sale_id" in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_record.py'), encoding='utf-8').read(), 'old drip table gets sale_id added (fixes 500 on /drip)')

import importlib, os as _o2
_rx = importlib.import_module('pharmacy.services.rx_scan')
_old_env = _o2.environ.get('TESSERACT_CMD'); _old_which = _rx.shutil.which
_o2.environ['TESSERACT_CMD'] = _o2.path.abspath(__file__)            # an existing file counts as configured
ok(_rx._tesseract_exe() == _o2.path.abspath(__file__), 'TESSERACT_CMD in .env is used first')
_o2.environ['TESSERACT_CMD'] = _o2.path.join(ROOT, 'no-such-tesseract.exe')
_rx.shutil.which = lambda name: None
ok(_rx._tesseract_exe() is None or _rx._tesseract_exe().lower().endswith('tesseract.exe'), 'missing TESSERACT_CMD falls back safely')
_rx.shutil.which = _old_which
if _old_env is None: _o2.environ.pop('TESSERACT_CMD', None)
else: _o2.environ['TESSERACT_CMD'] = _old_env
ok('contact_number' in open(_os.path.join(ROOT, 'database', 'schema.sql'), encoding='utf-8').read(), 'customer phone column is contact_number (schema)')
ok(' contact,' not in route and 'contact FROM' not in route, 'no query uses the non-existent customers.contact column')
route_src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
ok("getlist('drip_route[]')" in route_src and 'drip_routes=drip_routes' in route_src, 'counter sale reads the route per row and passes it on')
ok("route = (routes or {}).get(mid, AUTO_ROUTE)" in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_record.py'), encoding='utf-8').read(), 'drip record uses the chosen route, Not set otherwise')
new_src = open(_os.path.join(ROOT, 'templates', 'new_sale.html'), encoding='utf-8').read()
ok('name="drip_route[]"' in new_src and 'data-drip=' in new_src and 'function syncDripRoutes' in new_src, 'sale screen shows the route only for drip and injection rows')
failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
