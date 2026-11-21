"""Step 7 checks: barcode on medicines, duplicate barcode rule, scanner box on the sale page.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, re
from decimal import Decimal as D
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
# ---- routes with a mocked database ----
class Cur:
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split()); self.p = p
        Cur.last = self.sql
    def fetchone(self):
        s = self.sql
        if 'FROM users u JOIN roles' in s: return dict(user_id=1, full_name='Ahmed Ali', password_hash='h:admin123', role_name='Admin')
        if 'SELECT password_hash FROM users' in s: return dict(password_hash='h:admin123')
        if 'WHERE barcode' in s: return {'medicine_id': 7, 'name': 'Other'} if self.p[0] == 'TAKEN-1' else None
        if 'SELECT medicine_id FROM medicines WHERE LOWER(name)' in s: return None
        if 'information_schema' in s: return {'n': 1}
        if s.startswith('SELECT COUNT(*) AS total FROM medicines m'): return {'total': 1}
        if 'AS in_stock' in s: return {'total': 1, 'in_stock': 1, 'low': 0, 'out_count': 0}
        return {}
    def fetchall(self):
        s = self.sql
        if s.startswith('SELECT m.*, c.category_name'):
            return [{'medicine_id': 4, 'name': 'Panadol', 'category_id': 1, 'price': D('10'), 'cost_price': D('5'),
                     'stock_quantity': 30, 'reorder_level': 20, 'barcode': '8901234567890', 'category_name': 'Tablet'}]
        if s.startswith('SELECT m.medicine_id, m.name, m.barcode'):
            return [{'medicine_id': 5, 'name': 'Panadol', 'barcode': '8901234567890', 'price': D('10'), 'stock_quantity': 30,
                     'fresh_qty': 30, 'batch_count': 0}]
        if s.startswith('SELECT m.*'): return []
        return []
    def close(self): pass
class Conn:
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): pass
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = Conn()
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m

from pharmacy.lib import _read_medicine_form
from pharmacy.repos import medicines as med

RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))


# ---- form rules ----
base = {'name': 'Panadol', 'category_id': '1', 'price': '10', 'cost_price': '5', 'reorder': '20'}
d, e = _read_medicine_form(dict(base, barcode=' 8901234567890 '))
ok(e is None and d['barcode'] == '8901234567890', 'barcode is accepted and trimmed')
d, e = _read_medicine_form(dict(base))
ok(e is None and d['barcode'] is None, 'empty barcode is stored as NULL (no duplicate clash)')
d, e = _read_medicine_form(dict(base, barcode='12 34'))
ok(d is None and 'Barcode' in e, 'barcode with a space is rejected')
d, e = _read_medicine_form(dict(base, barcode='12'))
ok(d is None, 'barcode shorter than 4 characters is rejected')
d, e = _read_medicine_form(dict(base, barcode='abc<script>'))
ok(d is None, 'barcode with symbols is rejected')
d, e = _read_medicine_form(dict(base, barcode='A' * 65))
ok(d is None, 'barcode longer than 64 characters is rejected')
d, e = _read_medicine_form(dict(base, barcode='PAN-500'))
ok(e is None, 'dashes and letters are allowed')

# ---- repository ----
class FakeCur:
    def __init__(self, rows=None): self.calls = []; self.rows = list(rows or []); self.lastrowid = 9
    def execute(self, sql, p=None): self.calls.append((" ".join(sql.split()), p))
    def fetchone(self): return self.rows.pop(0) if self.rows else None
    def fetchall(self): return []
cur = FakeCur()
repo_data = {'name': 'Panadol', 'category_id': 1, 'price': 10, 'cost': 5, 'reorder': 20}
med.insert_medicine(cur, dict(repo_data, barcode='8901'), 0)
ok(cur.calls[0][1][1] == '8901', 'insert saves the barcode in the second column')
cur = FakeCur()
med.update_medicine(cur, 4, dict(repo_data, barcode=None))
ok('barcode=%s' in cur.calls[0][0] and cur.calls[0][1][1] is None, 'update sets the barcode (None clears it)')
cur = FakeCur([{'medicine_id': 2, 'name': 'X'}])
ok(med.find_medicine_by_barcode(cur, '8901', exclude_id=4)['medicine_id'] == 2, 'barcode lookup returns the other medicine')
ok('medicine_id <> %s' in cur.calls[0][0] and cur.calls[0][1] == ('8901', 4), 'barcode lookup on edit skips the same medicine')

import app as A
A.app.config['TESTING'] = False
c = A.app.test_client()
tok = re.search(r'name="csrf-token" content="([0-9a-f]+)"', c.get('/login').get_data(as_text=True)).group(1)
c.post('/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': tok})
with c.session_transaction() as s: tok2 = s['_csrf']

Cur.last = ''
r = c.post('/medicines/add', data={'csrf_token': tok2, 'name': 'Brufen', 'category_id': '1', 'price': '20',
                                    'barcode': 'TAKEN-1', 'stock': '0', 'reorder': '20'})
ok(not Cur.last.startswith('INSERT INTO medicines'), 'add with a barcode already used -> not saved')
ok(r.status_code == 302, 'duplicate barcode on add redirects back with a warning')

Cur.last = ''
c.post('/medicines/add', data={'csrf_token': tok2, 'name': 'Brufen', 'category_id': '1', 'price': '20',
                               'barcode': 'NEW-42', 'stock': '0', 'reorder': '20'})
ok(Cur.last.startswith('INSERT INTO medicines') and 'barcode' in Cur.last, 'add with a new barcode -> saved with barcode column')

r = c.get('/medicines')
t = r.get_data(as_text=True)
ok('openEdit(' in t and "'8901234567890', '', '')" in t, 'medicines page passes the barcode to the edit window')
ok('name="barcode"' in t and 'id="eBarcode"' in t, 'add and edit forms both have a barcode field')

r = c.get('/sales/new')
t = r.get_data(as_text=True)
ok('id="scanBox"' in t, 'sale page has the scanner box')
ok('data-barcode="8901234567890"' in t, 'medicine options carry their barcode for scanning')
ok("function scanCode(code)" in t and "e.key !== 'Enter'" in t, 'scanner reacts to Enter (USB scanners send Enter)')
ok('e.preventDefault()' in t, 'Enter in the scanner box does not submit the sale form')

_os.chdir(_cwd)
failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
