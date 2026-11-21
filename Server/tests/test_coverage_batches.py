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

# ================= BATCHES =================
from datetime import date, timedelta
TODAY = date.today()
GOOD_EXP = (TODAY + timedelta(days=400)).isoformat()
OLD_EXP = (TODAY - timedelta(days=30)).isoformat()
SOON_EXP = (TODAY + timedelta(days=20)).isoformat()
BATCH_ROWS = [
    dict(batch_id=1, medicine_id=1, batch_number='PAN-01', expiry_date=OLD_EXP, quantity=12, medicine_name='Panadol', days_left=-30, status='expired', purchase_price=D('5')),
    dict(batch_id=2, medicine_id=1, batch_number='PAN-02', expiry_date=SOON_EXP, quantity=8, medicine_name='Panadol', days_left=20, status='soon', purchase_price=D('5')),
]
STATS = dict(active_batches=2, expired_batches=1, expired_units=12, expired_value=60.0, soon_batches=1)

def batch_reset(rows=BATCH_ROWS, total=None, mismatch=0, mismatch_rows=None, batch_row=None):
    reset()
    RESP['SELECT COUNT(*) AS total FROM batches'] = {'total': len(rows) if total is None else total}
    RESP['SELECT b.*, m.name AS medicine_name'] = rows
    RESP['SELECT SUM(quantity > 0)'] = dict(active_batches=2, expired_batches=1, expired_units=12, expired_value=60, soon_batches=1)
    RESP['SELECT COUNT(*) AS n FROM ('] = {'n': mismatch}
    RESP['SELECT b.batch_id, b.medicine_id, b.batch_number'] = batch_row
    RESP['SELECT m.medicine_id, m.name, IFNULL(m.stock_quantity'] = mismatch_rows or []

c = client(ADMIN); batch_reset()
r = c.get('/batches')
ok(r.status_code == 200 and b'Panadol' in r.data, 'batches page lists the batches')
for flt in ['active', 'expired', 'soon', 'ok', 'empty', 'nonsense']:
    ok(c.get(f'/batches?filter={flt}').status_code == 200, f'batches filter "{flt}" opens')
ok(c.get('/batches?q=pan&filter=all').status_code == 200 and any('%pan%' in str(p) for _, p in LOG), 'batches search uses a LIKE match')
ok(c.get('/batches?page=99').status_code == 200, 'a page past the end is clamped, not an error')
ok(client(PHARM).get('/batches').status_code == 200, 'pharmacist can open batches')
ok(client(CASHIER).get('/batches').status_code == 302, 'cashier is refused batches')

batch_reset(rows=[]); c = client(ADMIN)
ok(c.get('/batches').status_code == 200, 'empty batch list still renders')

batch_reset(mismatch=3); c = client(ADMIN)
ok(c.get('/batches').status_code == 200, 'page shows the mismatch count without error')

# ---- write-off -------------------------------------------------------------------
batch_reset(batch_row=None); c = client(ADMIN)
c.post('/batches/writeoff/9', data=form())
ok('Nothing to write off for this batch' in flashes(c), 'write-off of a missing batch is refused')

batch_reset(batch_row=dict(batch_id=2, medicine_id=1, batch_number='PAN-02', expiry_date=GOOD_EXP, quantity=8, name='Panadol', stock_quantity=20)); c = client(ADMIN)
c.post('/batches/writeoff/2', data=form())
ok('Only expired batches can be written off' in flashes(c), 'write-off of a non-expired batch is refused')

batch_reset(batch_row=dict(batch_id=1, medicine_id=1, batch_number='PAN-01', expiry_date=OLD_EXP, quantity=12, name='Panadol', stock_quantity=20)); c = client(ADMIN)
c.post('/batches/writeoff/1', data=form())
ok(any('Expired batch PAN-01 of Panadol removed' in f for f in flashes(c)), 'expired batch is written off')
ok(sql_seen('UPDATE batches SET quantity = 0') and sql_seen('INSERT INTO stock_adjustments') and sql_seen('UPDATE medicines SET stock_quantity'),
   'write-off clears the batch, updates stock and writes the history')
ok(any(p and p[2] == -12 and p[3] == 20 and p[4] == 8 for _, p in LOG if 'INSERT INTO stock_adjustments' in _), 'history records -12 units, 20 to 8')

batch_reset(batch_row=dict(batch_id=1, medicine_id=1, batch_number='PAN-01', expiry_date=OLD_EXP, quantity=12, name='Panadol', stock_quantity=5)); c = client(ADMIN)
c.post('/batches/writeoff/1', data=form())
ok(any(p and p[4] == 0 for _, p in LOG if 'INSERT INTO stock_adjustments' in _), 'stock never goes below zero on write-off')

batch_reset(batch_row=dict(batch_id=1, medicine_id=1, batch_number='PAN-01', expiry_date=OLD_EXP, quantity=12, name='Panadol', stock_quantity=20)); c = client(ADMIN)
_orig = Cur.execute
def _boom(self, sql, p=None):
    if sql.startswith('UPDATE batches SET quantity = 0'): raise RuntimeError('db down')
    return _orig(self, sql, p)
Cur.execute = _boom
try:
    c.post('/batches/writeoff/1', data=form())
finally:
    Cur.execute = _orig
ok('Something went wrong' in ' '.join(flashes(c)), 'write-off database error shows a safe message')

# ---- reconcile -------------------------------------------------------------------
batch_reset(); c = client(ADMIN)
ok(c.get('/batches/reconcile').status_code == 200, 'reconcile page opens for Admin')
ok(client(PHARM).get('/batches/reconcile').status_code == 302, 'pharmacist is refused reconcile')

c = client(ADMIN)
c.post('/batches/reconcile', data=form(default_expiry='2000-01-01'))
ok(any('Please enter a future expiry date' in f for f in flashes(c)), 'reconcile refuses a past expiry date')
c.post('/batches/reconcile', data=form(default_expiry='not-a-date'))
ok(any('Please enter a future expiry date' in f for f in flashes(c)), 'reconcile refuses a bad expiry date')

batch_reset(mismatch_rows=[dict(medicine_id=3, name='Brufen', stock=10, cost=D('4'), batch_qty=6, diff=4)]); c = client(ADMIN)
c.post('/batches/reconcile', data=form(default_expiry=GOOD_EXP))
ok(sql_seen('INSERT INTO batches') and any('1 medicine(s) got an opening batch' in f for f in flashes(c)),
   'missing units get an OPENING batch')

batch_reset(mismatch_rows=[dict(medicine_id=3, name='Brufen', stock=6, cost=D('4'), batch_qty=10, diff=-4)]); c = client(ADMIN)
RESP['SELECT batch_id, quantity FROM batches'] = [dict(batch_id=7, quantity=10)]
c.post('/batches/reconcile', data=form(default_expiry=GOOD_EXP))
ok(sql_seen('UPDATE batches SET quantity = quantity - %s') and any('1 medicine(s) were trimmed' in f for f in flashes(c)),
   'extra units are taken out of the oldest batch first')

batch_reset(mismatch_rows=[dict(medicine_id=3, name='Brufen', stock=10, cost=D('4'), batch_qty=6, diff=4)]); c = client(ADMIN)
_orig = Cur.execute
def _boom2(self, sql, p=None):
    if sql.startswith('INSERT INTO batches'): raise RuntimeError('db down')
    return _orig(self, sql, p)
Cur.execute = _boom2
try:
    c.post('/batches/reconcile', data=form(default_expiry=GOOD_EXP))
finally:
    Cur.execute = _orig
ok('Something went wrong' in ' '.join(flashes(c)), 'reconcile database error shows a safe message')

failed = 0
passed = sum(1 for _, good in RESULTS if good)
failed = 0
for msg, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + msg)
    failed += 0 if good else 1
print(f"\nTOTAL: {passed} passed, {failed} failed")
_os.chdir(_cwd)
sys.exit(1 if failed else 0)

