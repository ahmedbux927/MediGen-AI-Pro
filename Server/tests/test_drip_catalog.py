"""v85: drip and injection list: CSV load, add, remove rules, and wiring. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import drip_catalog as DC
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

SAMPLE = ("﻿product_id,generic_name,category,dosage_form,common_strength_or_concentration,administration_route,"
          "prescription_required,notes,source_reference\n"
          "MED1,Sodium chloride 0.9%,IV Fluids,Infusion / IV solution,0.9%,IV,Yes,x,y\n"
          "MED2,Ceftriaxone,Antibiotic,Injection,1 g vial,IV/IM,Yes,x,y\n"
          "MED3,Melarsoprol,Antiparasitic,Injection,Product-specific,IV,No,x,y\n").encode('utf-8')
items, errs = DC.parse_catalog(SAMPLE)
ok(not errs and len(items) == 3, 'sample CSV with BOM reads 3 rows')
ok(items[0]['name'] == 'Sodium chloride 0.9%' and items[0]['dosage_form'] == 'Drip / IV fluid', 'infusion form becomes Drip / IV fluid, strength not doubled')
ok(items[1]['name'] == 'Ceftriaxone 1 g vial' and items[1]['dosage_form'] == 'Injection', 'name = generic + strength, form Injection')
ok(items[2]['name'] == 'Melarsoprol' and items[2]['rx_required'] == 0, 'placeholder strength is dropped, No = rx 0')
ok(items[0]['rx_required'] == 1 and items[0]['product_code'] == 'MED1', 'Yes = rx 1, product_id kept as product code')

_, e1 = DC.parse_catalog(b'generic_name,dosage_form\nParacetamol,Tablet\n')
ok(e1 and 'not an injection' in e1[0], 'a tablet row stops the whole file with a clear message')
_, e2 = DC.parse_catalog(b'name,price\nX,1\n')
ok(e2 and 'generic_name' in e2[0], 'a file without generic_name and dosage_form is refused')
_, e3 = DC.parse_catalog(b'\xff\xfe bad')
ok(e3 and 'UTF-8' in e3[0], 'non UTF-8 file is refused')
_, e4 = DC.parse_catalog(b'generic_name,dosage_form\n,Injection\n')
ok(e4 and 'empty' in e4[0], 'empty generic name is refused')
_, e5 = DC.parse_catalog(b'x' * (DC.MAX_BYTES + 5))
ok(e5 and '2 MB' in e5[0], 'file over 2 MB is refused')

real = _os.path.join(ROOT, 'tests', 'fixtures', 'drip_injection_list.csv')
if _os.path.exists(real):
    big, be = DC.parse_catalog(open(real, 'rb').read())
    ok(not be and len(big) > 300, 'the full drip and injection list loads (over 300 items)')

class FakeCur:
    def __init__(self, existing=(), history=0):
        self.existing, self.history, self.last, self.inserts = set(existing), history, None, []
        self.lastrowid = 77
    def execute(self, sql, params=()):
        self.last = (sql, params)
        if sql.startswith('SELECT medicine_id FROM medicines WHERE name'):
            self.rows = [{'medicine_id': 1}] if params[0] in self.existing else []
        elif sql.startswith('SELECT category_id'):
            self.rows = [{'category_id': 5}]
        elif sql.startswith('INSERT INTO medicines'):
            self.inserts.append(params)
        elif sql.startswith('SELECT COUNT(*)'):
            self.rows = [{'n': self.history}]
        else:
            self.rows = []
    def fetchone(self):
        return self.rows[0] if self.rows else None

cur = FakeCur(existing={'Ceftriaxone 1 g vial'})
added, skipped = DC.import_items(cur, items, 1, 'list.csv')
ok(added == 2 and skipped == 1, 'import adds new items and skips a name that already exists')
ok(cur.inserts and cur.inserts[0][-1] == 'list.csv', 'imported items record the source file')
ok('VALUES (%s,%s,0,0,0,0,' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_catalog.py'), encoding='utf-8').read(), 'imported items start with price 0, cost 0, stock 0 (set later)')
ok(DC.remove_blocker(FakeCur(history=0), 5) is None, 'an item with no history can be removed')
ok('cannot be deleted' in (DC.remove_blocker(FakeCur(history=3), 5) or ''), 'an item with sales or stock history cannot be removed')

route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'drip.py'), encoding='utf-8').read()
ok("'/drip/import'" in route and "'/drip/item/add'" in route and "'/drip/item/<int:mid>/remove'" in route, 'routes for load, add and remove exist')
ok("DC.parse_catalog(f.read(DC.MAX_BYTES + 1))" in route and "mysql.connection.commit()" in route, 'load reads at most the limit and commits once')
ok(route.count('@role_required') >= 5 and route.count("'Admin', 'Pharmacist'") >= 5, 'load, add and remove are for Admin and Pharmacist only')
tpl = open(_os.path.join(ROOT, 'templates', 'products.html'), encoding='utf-8').read()  # v86.13: drip.html removed; section page does this job
ok('enctype="multipart/form-data"' in tpl and 'name="catalog"' in tpl and tpl.count('name="csrf_token"') >= 3, 'upload and add forms carry the CSRF token')
ok('overflow-y:auto' in tpl and 'pd-scroll' in tpl, 'section page: table scrolls inside its card (Sell stays on screen)')
base = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
def read_hubs_inv():
    return open(_os.path.join(ROOT, 'pharmacy', 'routes', 'hubs.py'), encoding='utf-8').read()
ok(base.index("url_for('medicines_hub')") < base.index("url_for('inventory_hub')") and "'products_hub'" in read_hubs_inv(), 'Inventory hub lists Stock Overview; Medicines hub comes first in the sidebar')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
