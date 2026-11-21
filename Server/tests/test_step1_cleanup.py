"""Step 1 checks: manufacturer removed, role fixes, NaN rejected, schema migration, config key flag.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, os
from decimal import Decimal
sys.path.insert(0, ROOT); os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b''; bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
D = Decimal

class Cur:
    log = []
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split()); self.p = p; Cur.log.append((self.sql, p))
    def fetchone(self):
        s = self.sql
        if 'information_schema' in s: return {'n': 1}
        if 'SUM(stock_quantity > 0)' in s: return {'total': 0, 'in_stock': 0, 'low': 0, 'empty': 0, 'out_count': 0}
        if 'COUNT(*) AS total' in s: return {'total': 0}
        if 'COUNT(*) AS c FROM' in s: return {'c': 0}
        return None
    def fetchall(self): return []
    lastrowid = 1
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
A.app.template_folder = ROOT + '/templates'

ok = lambda c, msg: print(('PASS ' if c else 'FAIL ') + msg)
def login(role='Admin'):
    c = A.app.test_client(); c.get('/login')
    with c.session_transaction() as s: s.update(user_id=1, user_name='Ahmed', role=role); s['_csrf'] = 't'
    return c
def post(c, url, data=None):
    d = dict(data or {}); d['csrf_token'] = 't'
    return c.post(url, data=d)
def sqls(word):
    return [q for q, _ in Cur.log if word in q]

# 1. manufacturer UI and routes are gone
c = login('Admin')
MIGRATION_LOG = list(Cur.log)          # schema migration ran on the first request
h = c.get('/medicines').get_data(as_text=True)
ok(c.get('/medicines').status_code == 200 and 'Manufacturer' not in h and 'manufacturer' not in h.lower(), 'medicines page has no manufacturer text')
ok(post(c, '/manufacturers/add', {'manufacturer_name': 'X'}).status_code == 404, 'manufacturer add route removed (404)')
ok(c.get('/manage/manufacturers').status_code == 404, 'manufacturer page removed (404)')
ok('/manage/manufacturers' not in c.get('/dashboard').get_data(as_text=True), 'no manufacturer link in the menu')

# 2. medicine add/edit no longer touch manufacturer_id
Cur.log.clear()
post(c, '/medicines/add', {'name': 'Brufen 400', 'category_id': '1', 'price': '50', 'cost_price': '30', 'stock': '0', 'reorder': '10'})
ins = sqls('INSERT INTO medicines')
ok(ins and 'manufacturer' not in ins[0], 'add medicine: INSERT has no manufacturer column')
Cur.log.clear()
post(c, '/medicines/edit/3', {'name': 'Brufen', 'category_id': '1', 'price': '50', 'cost_price': '30', 'reorder': '10'})
upd = sqls('UPDATE medicines SET name')
ok(upd and 'manufacturer' not in upd[0], 'edit medicine: UPDATE has no manufacturer column')
Cur.log.clear()
post(c, '/medicines/add', {'name': 'NoCat', 'price': '5', 'stock': '0', 'reorder': '1'})
ok(not sqls('INSERT INTO medicines'), 'add medicine without category is refused')

# 3. role fixes from the audit
cash = login('Cashier')
Cur.log.clear(); post(cash, '/sales/7/pay', {'amount': '100', 'method': 'Cash'})
ok(not sqls('UPDATE sales SET paid_amount'), 'Cashier cannot receive payment')
Cur.log.clear(); post(cash, '/customers/delete/2')
ok(not sqls('DELETE FROM customers'), 'Cashier cannot delete a customer')
Cur.log.clear(); post(login('Pharmacist'), '/customers/delete/2')
ok(bool(sqls('DELETE FROM customers')), 'Pharmacist can still delete a customer')

# 4. NaN / inf are rejected
for bad in ('nan', 'inf', '-inf'):
    try:
        A._num(bad); ok(False, f'_num rejects {bad}')
    except ValueError:
        ok(True, f'_num rejects {bad}')
ok(A._num('12.5') == 12.5 and A._num('') == 0.0, '_num still reads normal numbers')
Cur.log.clear(); post(login('Admin'), '/sales/7/pay', {'amount': 'nan', 'method': 'Cash'})
ok(not sqls('UPDATE sales SET paid_amount'), 'payment of nan is not saved')

# 5. schema migration drops the link and the table (once, safely)
ok(any('DROP COLUMN manufacturer_id' in q for q, _ in MIGRATION_LOG), 'migration: manufacturer_id column dropped when present')
ok(any('DROP TABLE IF EXISTS manufacturers' in q for q, _ in MIGRATION_LOG), 'migration: manufacturers table dropped')

# 6. secret key: missing key is flagged, never a fixed known value
ok(isinstance(A.Config.SECRET_KEY_GENERATED, bool), 'config exposes SECRET_KEY_GENERATED flag')
ok(A.Config.SECRET_KEY != 'change-me-please' and len(A.Config.SECRET_KEY) >= 32, 'secret key is never the old fixed fallback')

# 7. records clear is audited (Admin, correct password)
print('INFO records-clear audit and the real migration are checked by tests/test_live_mysql.py (--live)')
