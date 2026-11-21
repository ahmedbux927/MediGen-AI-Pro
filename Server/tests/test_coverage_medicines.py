"""Sprint 4 coverage checks: users, account (login/forgot/profile/password), settings, records clear,
supplier-return POST and the /api/v1 error responses. Mock database (no MySQL).
Run through tests/run_all.py, or directly: python tests/test_coverage_admin.py"""
import os as _os, sys, types, io, re
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
from decimal import Decimal as D
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

class Row(dict):
    """Aggregate rows (COUNT/SUM) default to 0 so the route code never gets a KeyError."""
    def __missing__(self, key): return 0

# Fake database: RESP maps a SQL fragment to the row(s) returned. Set per test, cleared between tests.
RESP = {}
LOG = []
PASSWORD_HASH = {'value': 'h:admin123'}
class Cur:
    def execute(self, sql, p=None):
        self.sql = ' '.join(sql.split()); self.p = p; LOG.append((self.sql, p))
        self.rows = None
        for frag, val in RESP.items():
            if frag in self.sql:
                self.rows = val; break
        if self.rows is None and ('COUNT(' in self.sql or 'SUM(' in self.sql):
            self.rows = Row()
    def fetchone(self):
        r = self.rows
        if isinstance(r, list): return r[0] if r else None
        if r is None: return None
        return r
    def fetchall(self):
        r = self.rows
        if r is None: return []
        return r if isinstance(r, list) else [r]
    lastrowid = 7
    rowcount = 1
    def close(self): pass
class Conn:
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): pass
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = Conn()
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m

import app as A
from pharmacy import core
from pharmacy.api_auth import hash_token
core.mysql.connection = Conn()          # route modules read core.mysql, so point it at this suite's fake
app = A.app
app.config['TESTING'] = True
import pharmacy.routes  # noqa: F401  registers every URL, incl. /api/v1 and pwa

ADMIN = {'user_id': 1, 'role': 'Admin', 'user_name': 'Ahmed', '_csrf': 'tok123'}
PHARM = {'user_id': 2, 'role': 'Pharmacist', 'user_name': 'Ali', '_csrf': 'tok123'}
CASHIER = {'user_id': 3, 'role': 'Cashier', 'user_name': 'Sara', '_csrf': 'tok123'}

def client(sess=None):
    c = app.test_client()
    with c.session_transaction() as s:      # every client gets the same CSRF token the forms send
        s['_csrf'] = 'tok123'
        if sess:
            s.update(sess)
    return c
def reset():
    RESP.clear(); LOG.clear(); PASSWORD_HASH['value'] = 'h:admin123'
def form(**kw):
    kw.setdefault('csrf_token', 'tok123')
    return kw
def flashes(c):
    with c.session_transaction() as s:
        return [m for _, m in s.get('_flashes', [])]
def sql_seen(fragment):
    return any(fragment in s for s, _ in LOG)

# ================= MEDICINES (list, add, edit, stock adjust, history, delete, export) =================
import contextlib, datetime as _dt
@contextlib.contextmanager
def db_fails_on(prefix, exc=None):
    orig = Cur.execute
    def bad(self, sql, p=None):
        if sql.startswith(prefix): raise (exc or RuntimeError('db down'))
        return orig(self, sql, p)
    Cur.execute = bad
    try:
        yield
    finally:
        Cur.execute = orig

GOOD = dict(name='Panadol', price='12.50', cost_price='8', reorder='20', category_id='1', barcode='PAN1234', stock='10')
MED = dict(name='Panadol', stock_quantity=20, medicine_id=3)
def med_reset(**kw):
    reset()
    RESP['SELECT * FROM categories ORDER BY category_name'] = [dict(category_id=1, category_name='Tablet')]
    RESP['SELECT m.*, c.category_name'] = [dict(medicine_id=3, name='Panadol', category_name='Tablet', stock_quantity=20,
                                                  price=D('12.50'), cost_price=D('8'), reorder_level=20, barcode='PAN1234')]
    RESP['SELECT COUNT(*) AS total FROM medicines'] = {'total': 1}
    RESP['SELECT COUNT(*) AS total FROM medicines m'] = {'total': 1}
    RESP['SELECT medicine_id FROM medicines WHERE LOWER(name)'] = kw.get('by_name')
    RESP['SELECT medicine_id, name, strength FROM medicines'] = kw.get('by_name')   # v86.54 duplicate check
    RESP['SELECT medicine_id, name FROM medicines WHERE barcode'] = kw.get('by_barcode')
    RESP['SELECT name, stock_quantity FROM medicines WHERE medicine_id'] = kw.get('lock', dict(name='Panadol', stock_quantity=20))
    RESP['SELECT a.created_at'] = kw.get('history', [])
    RESP['SELECT batch_id, quantity FROM batches'] = kw.get('batches', [])

# list and filters
med_reset(); c = client(ADMIN)
ok(c.get('/medicines').status_code == 200, 'medicines list opens')
for f in ['low', 'out', 'ok', 'all', 'weird']:
    ok(c.get(f'/medicines?filter={f}').status_code == 200, f'medicines filter "{f}" opens')
ok(c.get('/medicines?q=pan&per=25&page=2').status_code == 200, 'search with a page size and page number')
ok(c.get('/medicines?per=7').status_code == 200, 'an unknown page size falls back to 15')
ok(client(CASHIER).get('/medicines').status_code == 200, 'cashier can open the medicines list')

# add
med_reset(); c = client(ADMIN); LOG.clear()
c.post('/medicines/add', data=form(**{k: v for k, v in GOOD.items() if k != 'name'}))
ok('Medicine name is required' in flashes(c), 'add refuses a missing name')
c.post('/medicines/add', data=form(**{**GOOD, 'price': 'abc'}))
ok('Invalid number format' in flashes(c), 'add refuses a price that is not a number')
c.post('/medicines/add', data=form(**{**GOOD, 'price': '-1'}))
ok('Price, cost and reorder level cannot be negative' in flashes(c), 'add refuses a negative price')
c.post('/medicines/add', data=form(**{**GOOD, 'category_id': ''}))
ok('Please choose a category' in flashes(c), 'add refuses a missing category')
c.post('/medicines/add', data=form(**{**GOOD, 'barcode': 'a b'}))
ok(any('Barcode must be' in f for f in flashes(c)), 'add refuses a barcode with spaces')
c.post('/medicines/add', data=form(**{**GOOD, 'stock': 'x'}))
ok('Invalid number format' in flashes(c), 'add refuses a stock value that is not a number')
c.post('/medicines/add', data=form(**{**GOOD, 'stock': '-3'}))
ok('Stock cannot be negative' in flashes(c), 'add refuses negative stock')

med_reset(by_name={'medicine_id': 3}); c = client(ADMIN)
c.post('/medicines/add', data=form(**GOOD))
ok(any('Duplicate:' in f and 'already exists' in f for f in flashes(c)), 'add refuses a duplicate name and strength')
med_reset(by_barcode={'medicine_id': 4, 'name': 'Other'}); c = client(ADMIN)
c.post('/medicines/add', data=form(**GOOD))
ok('This barcode is already used by another medicine.' in flashes(c), 'add refuses a duplicate barcode')

med_reset(); c = client(ADMIN); LOG.clear()
c.post('/medicines/add', data=form(**GOOD))
ok('Medicine added successfully' in flashes(c) and sql_seen('INSERT INTO medicines') and sql_seen('INSERT INTO stock_adjustments'),
   'a medicine is added with its opening stock history')
LOG.clear()
c.post('/medicines/add', data=form(**{**GOOD, 'stock': '0', 'barcode': ''}))
ok('Medicine added successfully' in flashes(c) and not sql_seen('INSERT INTO stock_adjustments'), 'zero opening stock writes no history row')
with db_fails_on('INSERT INTO medicines'):
    c.post('/medicines/add', data=form(**{**GOOD, 'barcode': ''}))
ok('Medicine could not be added' in ' '.join(flashes(c)) and 'Error E-102' in ' '.join(flashes(c)), 'add database error shows a safe message with code E-102')

# edit
med_reset(); c = client(ADMIN); LOG.clear()
c.post('/medicines/edit/3', data=form(**GOOD))
ok('Medicine updated successfully' in flashes(c) and sql_seen('UPDATE medicines SET name'), 'a medicine is edited')
c.post('/medicines/edit/3', data=form(**{**GOOD, 'name': ''}))
ok('Medicine name is required' in flashes(c), 'edit refuses a missing name')
med_reset(by_name={'medicine_id': 9}); c = client(ADMIN)
c.post('/medicines/edit/3', data=form(**GOOD))
ok(any('Duplicate:' in f for f in flashes(c)), 'edit refuses a name and strength used by another medicine')
med_reset(by_barcode={'medicine_id': 9, 'name': 'X'}); c = client(ADMIN)
c.post('/medicines/edit/3', data=form(**GOOD))
ok('This barcode is already used by another medicine.' in flashes(c), 'edit refuses a barcode used by another medicine')
med_reset(); c = client(ADMIN)
with db_fails_on('UPDATE medicines SET name'):
    c.post('/medicines/edit/3', data=form(**GOOD))
ok('Something went wrong' in ' '.join(flashes(c)), 'edit database error shows a safe message')

# stock adjust
med_reset(); c = client(ADMIN); LOG.clear()
c.post('/medicines/adjust/3', data=form(direction='in', reason='Found', quantity='5', note='shelf'))
ok('Stock of Panadol changed: 20 -> 25' in flashes(c) and sql_seen('UPDATE medicines SET stock_quantity'), 'stock in adds units')
RESP['SELECT batch_id, quantity FROM batches'] = [dict(batch_id=1, quantity=20)]
c.post('/medicines/adjust/3', data=form(direction='out', reason='Damaged', quantity='3'))
ok('Stock of Panadol changed: 20 -> 17' in flashes(c) and sql_seen('UPDATE batches SET quantity = quantity - %s'), 'stock out takes units from batches and is recorded')
c.post('/medicines/adjust/3', data=form(direction='out', reason='Damaged', quantity='999'))
ok(any('Only 20 units of Panadol are in stock' in f for f in flashes(c)), 'stock out above the stock is refused')
c.post('/medicines/adjust/3', data=form(direction='sideways', reason='Found', quantity='1'))
ok('Please choose in/out, a reason and a quantity above 0' in flashes(c), 'adjust refuses an unknown direction')
c.post('/medicines/adjust/3', data=form(direction='in', reason='Damaged', quantity='1'))
ok('Please choose in/out, a reason and a quantity above 0' in flashes(c), 'adjust refuses a reason that does not match the direction')
c.post('/medicines/adjust/3', data=form(direction='in', reason='Found', quantity='abc'))
ok('Please choose in/out, a reason and a quantity above 0' in flashes(c), 'adjust refuses a quantity that is not a number')
med_reset(lock=None); c = client(ADMIN)
c.post('/medicines/adjust/3', data=form(direction='in', reason='Found', quantity='1'))
ok('Medicine not found' in flashes(c), 'adjust of a missing medicine is refused')
med_reset(); c = client(ADMIN)
with db_fails_on('UPDATE medicines SET stock_quantity'):
    c.post('/medicines/adjust/3', data=form(direction='in', reason='Found', quantity='1'))
ok('Something went wrong' in ' '.join(flashes(c)), 'adjust database error shows a safe message')

# history
med_reset(history=[dict(created_at=_dt.datetime(2026, 10, 1, 9, 30), change_qty=5, old_stock=20, new_stock=25,
                        reason='Found', note=None, full_name='Ahmed')]); c = client(ADMIN)
r = c.get('/medicines/3/adjustments')
ok(r.status_code == 200 and r.get_json()[0]['by'] == 'Ahmed' and r.get_json()[0]['note'] == '', 'stock history returns JSON')

# delete
med_reset(); c = client(ADMIN); LOG.clear()
c.post('/medicines/delete/3', data=form())
ok('Medicine deleted' in flashes(c) and sql_seen('UPDATE medicines SET is_deleted'), 'an admin deletes a medicine (hidden, v86.29)')
LOG.clear()
ok(client(PHARM).post('/medicines/delete/3', data=form()).status_code == 302 and not sql_seen('DELETE FROM medicines'),
   'pharmacist cannot delete medicines (admin only)')
with db_fails_on('UPDATE medicines SET is_deleted', exc=Exception(1451, 'fk')):
    c.post('/medicines/delete/3', data=form())
ok(any('cannot be deleted' in f for f in flashes(c)), 'a medicine with history cannot be deleted')
with db_fails_on('UPDATE medicines SET is_deleted'):
    c.post('/medicines/delete/3', data=form())
ok('Something went wrong' in ' '.join(flashes(c)), 'other delete errors show a safe message')

# export
med_reset(); c = client(ADMIN)
r = c.get('/medicines/export')
ok(r.status_code == 200 and 'text/csv' in r.headers.get('Content-Type', ''), 'medicines export returns a CSV file')
r = c.get('/medicines/export?ids=3,x')
ok(r.status_code == 200, 'export with selected ids is accepted')

passed = sum(1 for _, good in RESULTS if good)
failed = 0
for msg, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + msg)
    failed += 0 if good else 1
print(f"\nTOTAL: {passed} passed, {failed} failed")
_os.chdir(_cwd)
sys.exit(1 if failed else 0)
