"""Product import (backend track, Phase 1): cell parsing, row checks, plan, all-or-nothing write,
the 230-product Word file conversion. Mock database only (no MySQL needed).
Run: python tests/test_product_import.py
"""
import os, sys, io, csv
from datetime import date, datetime
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import product_import as P          # noqa: E402

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

TODAY = date(2026, 10, 23)
SAMPLE_DOCX = os.path.join(ROOT, 'database', 'samples', 'MediGen_AI_Pro_230_Pharmacy_Products.docx')
SAMPLE_CSV = os.path.join(ROOT, 'database', 'samples', 'pharmacy_products_230_demo.csv')

# ---- cell parsing ----
ok(P.money('PKR 1,240') == Decimal('1240.00'), 'money: "PKR 1,240" -> 1240.00')
ok(P.money('Rs. 50.5') == Decimal('50.50'), 'money: "Rs. 50.5" -> 50.50')
ok(P.money('Verify brand / pack') is None and P.money('') is None, 'money: placeholder and blank -> NULL')
try:
    P.money('abc'); ok(False, 'money: text is rejected')
except ValueError:
    ok(True, 'money: text is rejected')
try:
    P.money('-5'); ok(False, 'money: negative is rejected')
except ValueError:
    ok(True, 'money: negative is rejected')
ok(P.barcode_of('2900000000001.0') == '2900000000001', 'barcode: Excel float suffix removed')
ok(P.barcode_of(' 290 000 ') == '290000', 'barcode: spaces removed')
try:
    P.barcode_of('AB12'); ok(False, 'barcode: letters rejected')
except ValueError:
    ok(True, 'barcode: letters rejected')
ok(P.rx_of('Yes') == 1 and P.rx_of('No (non-medicine)') == 0, 'rx: Yes -> 1, No -> 0')
ok(P.rx_of('Check local rules / pharmacist') is None, 'rx: unclear -> NULL (pharmacist must confirm, never "No")')
ok(P.date_of('2028-08-07') == date(2028, 8, 7) and P.date_of('07/08/2028') == date(2028, 8, 7), 'date: ISO and dd/mm/yyyy')
ok(P.date_of(datetime(2028, 8, 7, 10, 0)) == date(2028, 8, 7), 'date: Excel datetime accepted')
try:
    P.date_of('31-31-2028'); ok(False, 'date: impossible date rejected')
except ValueError:
    ok(True, 'date: impossible date rejected')

# ---- row checks ----
base = {'name': 'Test Syrup', 'selling_price': '200', 'purchase_price': '150', 'stock_quantity': '10',
        'batch_number': 'B1', 'expiry_date': '2028-01-01'}
row, errs, warns = P.check_row(base, TODAY)
ok(not errs and not warns, 'valid row: no errors, no warnings')
row, errs, _ = P.check_row({**base, 'name': ''}, TODAY); ok('name is required' in errs, 'missing name is an error')
row, errs, _ = P.check_row({**base, 'expiry_date': '2026-01-01'}, TODAY); ok('expiry date has already passed' in errs, 'past expiry is an error')
row, errs, warns = P.check_row({**base, 'expiry_date': '2026-11-10'}, TODAY)
ok(not errs and any('within 30 days' in w for w in warns), 'expiry within 30 days is a warning')
row, errs, warns = P.check_row({**base, 'purchase_price': '300'}, TODAY)
ok(any('higher than selling' in w for w in warns), 'cost above selling price is a warning (shop data had such rows)')
row, errs, warns = P.check_row({**base, 'batch_number': '', 'expiry_date': ''}, TODAY)
ok(any('no batch' in w for w in warns), 'stock without batch and expiry is a warning')
row, errs, _ = P.check_row({**base, 'selling_price': 'x'}, TODAY)
ok(any(e.startswith('selling_price') for e in errs) and 'selling price is required' not in errs, 'bad price gives one clear error')
row, errs, _ = P.check_row({**base, 'strength': 'Verify exact SKU / N/A'}, TODAY)
ok(row['strength'] is None and not errs, 'placeholder strength is stored as NULL, not an error')
row, errs, _ = P.check_row({**base, 'stock_quantity': '1.5'}, TODAY)
ok(any('whole number' in e for e in errs), 'fractional stock is an error')

# ---- reading files ----
csv_bytes = '﻿Product Name,Price,Qty,Extra\nPanadol,PKR 100,5,x\n'.encode('utf-8')
rows, hw = P.read_file(csv_bytes, 'list.csv')
ok(rows[0]['name'] == 'Panadol' and rows[0]['selling_price'] == 'PKR 100', 'csv: BOM removed, header aliases mapped')
ok(any('ignored column' in w and 'extra' in w for w in hw), 'csv: unknown column reported, not silently used')
try:
    P.read_file('Name,Stock\nA,1\n'.encode(), 'bad.csv'); ok(False, 'csv: missing selling price column rejected')
except ValueError as e:
    ok('selling_price' in str(e), 'csv: missing selling price column rejected')
try:
    P.read_file(b'x', 'list.txt'); ok(False, 'other file types rejected')
except ValueError:
    ok(True, 'other file types rejected')
try:
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    ws.append(['Product Name', 'Selling Price', 'Barcode'])
    ws.append(['Brufen', 90, 2900000000111.0])
    buf = io.BytesIO(); wb.save(buf)
    rows, _ = P.read_file(buf.getvalue(), 'list.xlsx')
    ok(rows[0]['name'] == 'Brufen' and rows[0]['barcode'] == 2900000000111.0, 'xlsx: read with header aliases')
except ImportError:
    print('SKIP xlsx (openpyxl not installed)')

# ---- the 230-product file ----
data_rows, _ = P.read_file(open(SAMPLE_CSV, 'rb').read(), 'pharmacy_products_230_demo.csv')
ok(len(data_rows) == 230, 'sample CSV has 230 products')
plan, summ = P.build_plan(data_rows, {'barcodes': {}, 'names': {}}, TODAY)
ok(summ['counts'] == {'create': 230, 'update': 0, 'skip': 0, 'error': 0} and summ['can_commit'],
   'all 230 products are valid and would be created')
ok(summ['missing_fields']['rx_required'] == 165, 'unclear Rx flag counted (165 rows) for the pharmacist to confirm')
ok(summ['missing_fields']['strength'] == 230, 'unverified strength counted (all rows marked "Verify")')

def docx_rows():
    import importlib.util
    spec = importlib.util.spec_from_file_location('conv', os.path.join(ROOT, 'scripts', 'docx_products_to_csv.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.read_products(SAMPLE_DOCX)
conv = docx_rows()
committed = list(csv.DictReader(open(SAMPLE_CSV, encoding='utf-8')))
ok(len(conv) == 230 and [r['barcode'] for r in conv] == [r['barcode'] for r in committed],
   'docx converter gives the same 230 barcodes as the committed CSV')
ok(conv[0]['selling_price'] == '1488.00' and conv[0]['category'] == 'Painkillers & Fever Medicines',
   'docx converter: price cleaned, category kept')

existing = {'barcodes': {'123456789': {'medicine_id': 17, 'name': 'nebrol fort', 'barcode': '123456789'}},
            'names': {'panadol': {'medicine_id': 1, 'name': 'Panadol', 'barcode': None}}}
plan2, summ2 = P.build_plan(data_rows, existing, TODAY)
ok(summ2['counts']['skip'] == 1 and [i['name'] for i in plan2 if i['action'] == 'skip'] == ['Panadol'],
   'existing item matched by name is skipped by default')
plan3, summ3 = P.build_plan(data_rows, existing, TODAY, update_existing=True)
ok(summ3['counts']['update'] == 1 and summ3['counts']['create'] == 229, 'with --update-existing the match is updated, not created twice')

dup = data_rows[:2] + [dict(data_rows[0], product_code='X')]
plan4, summ4 = P.build_plan(dup, {'barcodes': {}, 'names': {}}, TODAY)
ok(summ4['counts']['error'] == 1 and not summ4['can_commit'], 'repeated item in one file is an error and blocks the write')
bad = data_rows[:1] + [dict(data_rows[1], selling_price='abc')]
plan5, summ5 = P.build_plan(bad, {'barcodes': {}, 'names': {}}, TODAY)
ok(not summ5['can_commit'], 'one bad row blocks the whole import (all-or-nothing)')

# ---- writing (fake cursor: records every statement) ----
class FakeCur:
    def __init__(self):
        self.log, self.lastrowid, self.categories = [], 500, [{'category_id': 1, 'category_name': 'Antibiotics'}]
        self._last = None
    def execute(self, sql, params=None):
        self.log.append((' '.join(sql.split()), params))
        self._last = sql
        if sql.startswith('INSERT INTO categories') or sql.startswith('INSERT INTO medicines') or sql.startswith('INSERT INTO batches'):
            self.lastrowid += 1
    def fetchall(self):
        return self.categories if self._last and 'FROM categories' in self._last else []
    def close(self):
        pass

audits = []
def fake_audit(cur, action, entity=None, entity_id=None, details='', before=None, after=None, status='ok'):
    audits.append((action, entity_id))

small = [dict(data_rows[0]), dict(data_rows[1], category='Antibiotics'), dict(data_rows[2], stock_quantity='0', batch_number='', expiry_date='')]
plan6, _ = P.build_plan(small, {'barcodes': {}, 'names': {}}, TODAY)
cur = FakeCur()
done = P.apply_plan(cur, plan6, 'test.csv', audit_fn=fake_audit)
inserts_med = [s for s, _ in cur.log if s.startswith('INSERT INTO medicines')]
inserts_bat = [s for s, _ in cur.log if s.startswith('INSERT INTO batches')]
ok(done['created'] == 3 and len(inserts_med) == 3, 'apply: three medicines created')
ok(done['batches'] == 2 and len(inserts_bat) == 2, 'apply: one batch per product with stock, none when stock is 0')
ok(done['categories_added'] == 1 and sum(1 for s, _ in cur.log if s.startswith('INSERT INTO categories')) == 1,
   'apply: new category created once (shared by two rows), existing one reused')
ok(len(audits) == 3 and all(a == 'medicine.import' for a, _ in audits), 'apply: one audit row per new medicine')
ok(all('import_source' in s for s in inserts_med), 'apply: import source recorded on every medicine')

cur2 = FakeCur()
upd_plan, _ = P.build_plan([dict(data_rows[0], selling_price='1600', stock_quantity='999')],
                           existing, TODAY, update_existing=True)
done2 = P.apply_plan(cur2, upd_plan, 'test.csv', audit_fn=fake_audit)
upd_sql = [s for s, _ in cur2.log if s.startswith('UPDATE medicines')]
ok(done2['updated'] == 1 and upd_sql and 'stock_quantity' not in upd_sql[0] and 'price = %s' in upd_sql[0],
   'update: price changes, stock never changes (stock goes through audited adjustments)')
ok(not any(s.startswith('INSERT INTO batches') for s, _ in cur2.log), 'update: no batch is created for an existing item')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
