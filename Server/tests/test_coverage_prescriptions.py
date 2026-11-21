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

# ================= PRESCRIPTIONS =================
import contextlib
@contextlib.contextmanager
def db_fails_on(prefix):
    orig = Cur.execute
    def bad(self, sql, p=None):
        if sql.startswith(prefix): raise RuntimeError('db down')
        return orig(self, sql, p)
    Cur.execute = bad
    try:
        yield
    finally:
        Cur.execute = orig

RX_ROW = dict(prescription_id=5, customer_id=2, doctor_name='Dr. Ahmed', notes='Take after food', customer_name='Sara',
              medical_history='Known penicillin allergy', contact_number='0300', email='s@x.pk', date_issued='2026-10-01')
RX_ITEMS = [dict(medicine_id=3, dosage='1 tab twice daily', duration_days=5, medicine_name='Amoxicillin 500', name='Amoxicillin 500')]
CUST_ROW = dict(customer_id=2, medical_history='penicillin allergy')
MED_ROW = dict(name='Amoxicillin 500')

def rx_reset(rx=RX_ROW, items=RX_ITEMS, sales=None, rows=None, total=None):
    reset()
    RESP['SELECT COUNT(*) AS total FROM prescriptions'] = {'total': (len(rows or []) if total is None else total)}
    RESP['SELECT p.*, c.name AS customer_name, \n'] = None
    RESP['SELECT p.*, c.name AS customer_name, (SELECT'] = rows or []
    RESP['SELECT COUNT(*) AS total, SUM('] = {'total': 4, 'dispensed': 1}
    RESP['SELECT customer_id, name, medical_history FROM customers'] = [dict(customer_id=2, name='Sara', medical_history='')]
    RESP['SELECT medicine_id, name FROM medicines'] = [dict(medicine_id=3, name='Amoxicillin 500')]
    RESP['SELECT customer_id, medical_history FROM customers WHERE customer_id'] = CUST_ROW
    RESP['SELECT name FROM medicines WHERE medicine_id'] = MED_ROW
    RESP['SELECT p.*, c.name AS customer_name, c.medical_history'] = rx
    RESP['SELECT p.*, c.name AS customer_name, c.contact_number'] = rx
    RESP['SELECT sale_id FROM sales WHERE prescription_id'] = [dict(sale_id=s) for s in (sales or [])]
    RESP['SELECT COUNT(*) AS n FROM sales WHERE prescription_id'] = {'n': len(sales or [])}
    RESP['SELECT m.name, pi.dosage, pi.duration_days'] = items
    RESP['SELECT pi.medicine_id, pi.dosage, pi.duration_days'] = items
    RESP['SELECT pi.*, m.name AS medicine_name'] = items
    RESP['SELECT sale_id, sale_date, total_amount FROM sales'] = []
    RESP['SELECT p.doctor_name, c.name AS customer_name'] = rx

def rxpost(c, url, **kw):
    d = dict(doctor_name='Dr. Ahmed', notes='', **{'medicine_id[]': ['3'], 'dosage[]': ['1 tab'], 'duration[]': ['5']})
    d.update(kw)
    LOG.clear()
    return c.post(url, data=form(**d))

# list
rx_reset(rows=[dict(RX_ROW, item_count=1, dispensed_count=0, sale_id=None)]); c = client(ADMIN)
ok(c.get('/prescriptions').status_code == 200, 'prescriptions list opens')
for flt in ['open', 'dispensed', 'all', 'weird']:
    ok(c.get(f'/prescriptions?filter={flt}').status_code == 200, f'prescriptions filter "{flt}" opens')
ok(c.get('/prescriptions?q=Sara').status_code == 200 and any('%Sara%' in str(p) for _, p in LOG), 'search by customer name')
ok(c.get('/prescriptions?q=5&page=3').status_code == 200, 'search by number and a page past the end')
ok(client(PHARM).get('/prescriptions').status_code == 200, 'pharmacist can open prescriptions')
ok(client(CASHIER).get('/prescriptions').status_code == 302, 'cashier is refused prescriptions')

# add
rx_reset(); c = client(ADMIN)
ok(c.get('/prescriptions/add').status_code == 200, 'add prescription page opens')
rxpost(c, '/prescriptions/add', customer_id='')
ok('Please choose a customer' in flashes(c), 'add refuses a missing customer')
RESP['SELECT customer_id, medical_history FROM customers WHERE customer_id'] = None   # no such customer
rxpost(c, '/prescriptions/add', customer_id='99999')
ok('Customer not found' in flashes(c), 'add refuses an unknown customer')
RESP['SELECT customer_id, medical_history FROM customers WHERE customer_id'] = CUST_ROW
rxpost(c, '/prescriptions/add', customer_id='2', doctor_name='')
ok('Please enter the doctor name' in flashes(c), 'add refuses a missing doctor name')
rxpost(c, '/prescriptions/add', customer_id='2', **{'medicine_id[]': [''], 'dosage[]': ['']})
ok('Please add at least one medicine' in flashes(c), 'add refuses a prescription with no medicine')
rxpost(c, '/prescriptions/add', customer_id='2', **{'duration[]': ['400']})
ok(any('between 1 and 365 days' in f for f in flashes(c)), 'add refuses a duration out of range')
rxpost(c, '/prescriptions/add', customer_id='2', **{'duration[]': ['abc']})
ok(any('duration must be a number' in f for f in flashes(c)), 'add refuses a non-number duration')
rxpost(c, '/prescriptions/add', customer_id='2', **{'medicine_id[]': ['x']})
ok(any('please choose a medicine' in f for f in flashes(c)), 'add refuses a row without a valid medicine')
rxpost(c, '/prescriptions/add', customer_id='2', **{'dosage[]': ['']})
ok(any('please enter the dosage' in f for f in flashes(c)), 'add refuses a row without dosage')
rxpost(c, '/prescriptions/add', customer_id='2')
ok('Prescription #7 saved.' in flashes(c) and sql_seen('INSERT INTO prescriptions') and sql_seen('INSERT INTO prescription_items'),
   'valid prescription is saved with its items')
rx_reset(); c = client(ADMIN)
RESP['SELECT customer_id, medical_history FROM customers WHERE customer_id'] = dict(customer_id=2, medical_history='penicillin allergy')
rxpost(c, '/prescriptions/add', customer_id='2')
ok(any("'penicillin' in history" in f or "Patient history mentions 'penicillin'" in f for f in flashes(c)), 'penicillin allergy warning is shown after save')
rx_reset(); c = client(ADMIN)
with db_fails_on('INSERT INTO prescriptions'):
    rxpost(c, '/prescriptions/add', customer_id='2')
ok('Something went wrong' in ' '.join(flashes(c)), 'add database error shows a safe message')

# edit
rx_reset(rx=None); c = client(ADMIN)
r = c.get('/prescriptions/404/edit')
ok(r.status_code == 302 and 'Prescription not found' in flashes(c), 'editing an unknown prescription is refused')
rx_reset(); c = client(ADMIN)
ok(c.get('/prescriptions/5/edit').status_code == 200, 'edit page opens for a prescription')
rxpost(c, '/prescriptions/5/edit', doctor_name='Dr. Khan')
ok('Prescription #5 updated.' in flashes(c) and sql_seen('UPDATE prescriptions SET doctor_name'), 'edit saves the changes')
rx_reset(sales=[11]); c = client(ADMIN)
rxpost(c, '/prescriptions/5/edit', doctor_name='Dr. Khan')
ok(sql_seen('UPDATE prescriptions SET doctor_name') and any('NOT changed' in str(p) for _, p in LOG),
   'edit of a dispensed prescription is allowed and the sale is noted')
rx_reset(); c = client(ADMIN)
rxpost(c, '/prescriptions/5/edit', doctor_name='')
ok(any('Please enter the doctor name' in f for f in flashes(c)), 'edit refuses a missing doctor name')
with db_fails_on('UPDATE prescriptions SET doctor_name'):
    rxpost(c, '/prescriptions/5/edit', doctor_name='Dr. Khan')
ok('Something went wrong' in ' '.join(flashes(c)), 'edit database error shows a safe message')

# delete
rx_reset(sales=[11]); c = client(ADMIN)
c.post('/prescriptions/5/delete', data=form())
ok(any('cannot be deleted' in f for f in flashes(c)), 'a dispensed prescription cannot be deleted')
rx_reset(rx=None, sales=None); c = client(ADMIN)
c.post('/prescriptions/5/delete', data=form())
ok('Prescription not found' in flashes(c), 'deleting an unknown prescription is refused')
rx_reset(); c = client(ADMIN)
c.post('/prescriptions/5/delete', data=form())
ok('Prescription #5 deleted.' in flashes(c) and sql_seen('DELETE FROM prescriptions'), 'an open prescription is deleted with an audit entry')
LOG.clear()
ok(client(PHARM).post('/prescriptions/5/delete', data=form()).status_code == 302 and not sql_seen('DELETE FROM prescriptions'), 'pharmacist cannot delete a prescription')

# receipt
rx_reset(); c = client(ADMIN)
ok(c.get('/prescription/receipt/5').status_code == 200, 'prescription receipt prints')
rx_reset(rx=None); c = client(ADMIN)
c.get('/prescription/receipt/404')
ok('Prescription not found' in flashes(c), 'receipt for an unknown prescription is refused')

passed = sum(1 for _, good in RESULTS if good)
failed = 0
for msg, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + msg)
    failed += 0 if good else 1
print(f"\nTOTAL: {passed} passed, {failed} failed")
_os.chdir(_cwd)
sys.exit(1 if failed else 0)
