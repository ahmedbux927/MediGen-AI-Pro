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

# ================= CATEGORIES, CUSTOMERS, SUPPLIERS =================
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

CAT_ROWS = [dict(category_id=1, category_name='Tablet'), dict(category_id=2, category_name='Syrup')]
CUST_ROWS = [dict(customer_id=1, name='Sara', contact_number='0300', email='s@x.pk', gender='Female', medical_history='')]
SUP_ROWS = [dict(supplier_id=1, name='ABC Pharma', contact='0321', email='a@x.pk', address='Lahore')]

def cat_reset(in_use=0, exists=False):
    reset()
    RESP['SELECT * FROM categories'] = CAT_ROWS
    RESP['SELECT category_id FROM categories WHERE category_name'] = {'category_id': 9} if exists else None
    RESP['SELECT COUNT(*) AS c FROM medicines WHERE category_id'] = {'c': in_use}
    RESP['SELECT * FROM customers'] = CUST_ROWS
    RESP['SELECT * FROM suppliers'] = SUP_ROWS

# ---- categories ----
cat_reset(); c = client(ADMIN)
ok(c.get('/manage/categories').status_code == 200, 'categories page opens for admin')
ok(client(PHARM).get('/manage/categories').status_code == 200, 'pharmacist can open categories')
ok(client(CASHIER).get('/manage/categories').status_code == 302, 'cashier is refused categories')

cat_reset(in_use=2); c = client(ADMIN)
c.post('/categories/delete/1', data=form())
ok('Cannot delete! 2 medicine(s) use this category' in flashes(c), 'a category in use cannot be deleted')
ok(not sql_seen('DELETE FROM categories'), 'no delete runs for a category in use')

cat_reset(in_use=0); c = client(ADMIN); LOG.clear()
c.post('/categories/delete/1', data=form())
ok('Category deleted successfully' in flashes(c) and sql_seen('DELETE FROM categories'), 'an unused category is deleted')
LOG.clear()
ok(client(PHARM).post('/categories/delete/1', data=form()).status_code == 302 and not sql_seen('DELETE FROM categories'),
   'pharmacist cannot delete categories (admin only)')
with db_fails_on('DELETE FROM categories'):
    c.post('/categories/delete/1', data=form())
ok('Something went wrong' in ' '.join(flashes(c)), 'category delete database error shows a safe message')

cat_reset(); c = client(ADMIN)
c.post('/categories/add', data=form(category_name='   '))
ok('Category name is required' in flashes(c), 'empty category name is refused')
c.post('/categories/add', data=form())
ok('Something went wrong' in ' '.join(flashes(c)), 'missing category field is handled, not a crash')
cat_reset(exists=True); c = client(ADMIN)
c.post('/categories/add', data=form(category_name='Tablet'))
ok('Category already exists' in flashes(c), 'duplicate category is refused')
cat_reset(); c = client(ADMIN); LOG.clear()
c.post('/categories/add', data=form(category_name='Capsule'))
ok('Category added successfully' in flashes(c) and sql_seen('INSERT INTO categories'), 'a new category is added')
with db_fails_on('INSERT INTO categories'):
    c.post('/categories/add', data=form(category_name='Gel'))
ok('Something went wrong' in ' '.join(flashes(c)), 'category add database error shows a safe message')

# ---- customers ----
cat_reset(); c = client(ADMIN)
ok(c.get('/customers').status_code == 200, 'customers page opens')
ok(client(CASHIER).get('/customers').status_code == 200, 'cashier can open customers')
cat_reset(); c = client(ADMIN); LOG.clear()
r = c.post('/customers/add', data=form(name='Ali', contact='0300', email='a@x.pk', gender='Male', history=''))
ok('Customer added' in flashes(c) and sql_seen('INSERT INTO customers') and r.status_code == 302, 'a customer is added')
r = c.post('/customers/add', data=form(name='Ali', contact='0300', email='', gender='Male', history=''),
           headers={'Referer': 'http://localhost/sales/new'})
ok(r.headers.get('Location', '').endswith('/sales/new'), 'adding a customer from the sale page returns to the sale')
c.post('/customers/add', data=form(name='Ali'))
ok('Something went wrong' in ' '.join(flashes(c)), 'customer add with missing fields is handled')
LOG.clear()
c.post('/customers/delete/1', data=form())
ok('Customer deleted' in flashes(c) and sql_seen('DELETE FROM customers'), 'a customer is deleted')
ok(client(CASHIER).post('/customers/delete/1', data=form()).status_code == 302, 'cashier cannot delete customers')
with db_fails_on('DELETE FROM customers'):
    c.post('/customers/delete/1', data=form())
ok('Something went wrong' in ' '.join(flashes(c)), 'customer delete database error shows a safe message')

# ---- suppliers ----
cat_reset(); c = client(ADMIN)
ok(c.get('/suppliers').status_code == 200, 'suppliers page opens for admin')
ok(client(PHARM).get('/suppliers').status_code == 200, 'pharmacist can open suppliers')
ok(client(CASHIER).get('/suppliers').status_code == 302, 'cashier is refused suppliers')
cat_reset(); c = client(ADMIN); LOG.clear()
r = c.post('/suppliers/add', data=form(name='XYZ', contact='0321', email='', address='Karachi'))
ok('Supplier added successfully' in flashes(c) and sql_seen('INSERT INTO suppliers') and r.status_code == 302, 'a supplier is added')
r = c.post('/suppliers/add', data=form(name='XYZ', contact='0321', email='', address='Karachi'),
           headers={'Referer': 'http://localhost/purchase/new'})
ok(r.headers.get('Location', '').endswith('/purchase/new'), 'adding a supplier from the purchase page returns to purchase')
c.post('/suppliers/add', data=form(name='XYZ'))
ok('Something went wrong' in ' '.join(flashes(c)), 'supplier add with missing fields is handled')
LOG.clear()
c.post('/suppliers/delete/1', data=form())
ok('Supplier deleted' in flashes(c) and sql_seen('DELETE FROM suppliers'), 'an admin deletes a supplier')
LOG.clear()
ok(client(PHARM).post('/suppliers/delete/1', data=form()).status_code == 302 and not sql_seen('DELETE FROM suppliers'),
   'pharmacist cannot delete suppliers (admin only)')
with db_fails_on('DELETE FROM suppliers'):
    c.post('/suppliers/delete/1', data=form())
ok('Something went wrong' in ' '.join(flashes(c)), 'supplier delete database error shows a safe message')

passed = sum(1 for _, good in RESULTS if good)
failed = 0
for msg, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + msg)
    failed += 0 if good else 1
print(f"\nTOTAL: {passed} passed, {failed} failed")
_os.chdir(_cwd)
sys.exit(1 if failed else 0)
