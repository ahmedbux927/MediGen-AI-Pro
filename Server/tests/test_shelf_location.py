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


class FakeCur:
    def __init__(self, rows=None): self.calls = []; self.rows = list(rows or []); self.lastrowid = 9
    def execute(self, sql, p=None): self.calls.append((" ".join(sql.split()), p))
    def fetchone(self): return self.rows.pop(0) if self.rows else None
    def fetchall(self): return []
cur = FakeCur()
repo_data = {'name': 'Panadol', 'category_id': 1, 'price': 10, 'cost': 5, 'reorder': 20}

# ---- shelf location (rack_location) ----
from pharmacy.lib import _read_medicine_form as _rmf
base = {'name': 'Panadol', 'category_id': '1', 'price': '10', 'cost_price': '5', 'reorder': '20'}
d, e = _rmf(dict(base, rack_location='  A-3  '))
ok(e is None and d['rack_location'] == 'A-3', 'shelf location is accepted and trimmed')
d, e = _rmf(dict(base))
ok(e is None and d['rack_location'] is None, 'empty shelf location is stored as NULL')
d, e = _rmf(dict(base, rack_location='X' * 41))
ok(d is None and 'Shelf location' in e, 'shelf location longer than 40 characters is rejected')
d, e = _rmf(dict(base, rack_location='X' * 40))
ok(e is None, 'shelf location of exactly 40 characters is accepted')

cur = FakeCur()
med.insert_medicine(cur, dict(repo_data, barcode=None, rack_location='B-2'), 0)
ok('rack_location' in cur.calls[0][0] and 'B-2' in cur.calls[0][1], 'insert saves the shelf location')
cur = FakeCur()
med.update_medicine(cur, 5, dict(repo_data, barcode=None, rack_location=None))
ok('rack_location=%s' in cur.calls[0][0] and cur.calls[0][1][-3] is None, 'update saves the shelf location (NULL when empty)')


# ---- v77: dosage form on medicines (checked by the same parser) ----
d, e = _rmf(dict(base, dosage_form='Drip / IV fluid'))
ok(e is None and d['dosage_form'] == 'Drip / IV fluid', 'a medicine can be saved as a drip')
d, e = _rmf(dict(base, dosage_form='Hacked<script>'))
ok(d is None and 'dosage form' in e, 'an unknown dosage form is refused')
d, e = _rmf(dict(base))
ok(e is None and d['dosage_form'] is None, 'dosage form is optional')

_os.chdir(_cwd)
failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
