"""v52 dashboard backend: recent_sales, top_med_revenue, pending_po (read-only SELECTs). Mock DB only.
Run: python tests/test_dashboard_backend.py
"""
import os, sys, types, datetime
from decimal import Decimal as D
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc

class FakeCur:
    log = []
    def execute(self, sql, p=None):
        self.sql = ' '.join(sql.split())
        FakeCur.log.append(self.sql)
    def fetchone(self):
        if 'purchase_orders' in self.sql:
            return {'c': 3}
        return {'c': 0, 's': 0}
    def fetchall(self):
        s = self.sql
        if 'FROM sales s' in s and 'Walk-in' in s:
            return [
                {'sale_id': 7, 'sale_date': datetime.datetime(2026, 10, 23, 18, 5), 'total_amount': D('450.00'),
                 'returned_amount': D('0.00'), 'customer': 'Walk-in'},
                {'sale_id': 6, 'sale_date': datetime.datetime(2026, 10, 22, 9, 0), 'total_amount': D('120.00'),
                 'returned_amount': D('20.00'), 'customer': 'Ali'},
            ]
        if 'SUM(si.subtotal) AS revenue' in s:
            return [{'name': 'Panadol', 'revenue': D('5000.00'), 'sold': 50},
                    {'name': 'Brufen', 'revenue': None, 'sold': 4}]
        return []
    def close(self): pass

class FakeConn:
    def cursor(self): return FakeCur()
    def commit(self): pass
    def rollback(self): pass

m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = FakeConn()
m.MySQL = MySQL
sys.modules['flask_mysqldb'] = m

import app as A
import pharmacy.routes  # noqa: F401
A.app.config['TESTING'] = True
A.app.config['SESSION_COOKIE_SECURE'] = False
A.mysql.connection = FakeConn()

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

captured = {}
import flask
def fake_render(template, **ctx):
    captured.update(ctx)
    return 'ok'

import pharmacy.routes.dashboard as DB
DB.render_template = fake_render

c = A.app.test_client(); c.get('/login')
with c.session_transaction() as s:
    s.update(user_id=1, user_name='Ahmed', role='Admin'); s['_csrf'] = 't'
r = c.get('/dashboard')
ok(r.status_code == 200, 'dashboard responds 200 with the mock database')
ok(captured.get('pending_po') == 3, 'pending_po comes from the Pending purchase order count')
rs = captured.get('recent_sales', [])
ok('recent_sales' not in open('pharmacy/routes/dashboard.py', encoding='utf-8').read(), 'v86.76: the recent sales list was removed from the dashboard (owner request)')
ok(captured.get('top_med_revenue') == [5000.0, 0.0], 'top_med_revenue is float and 0 when revenue is NULL')
ok(captured.get('top_med_names') == ['Panadol', 'Brufen'], 'top_med_names order unchanged')
ok(captured.get('top_med_sold') == [50, 4], 'top_med_sold unchanged')
ok(any('SUM(si.subtotal) AS revenue' in q for q in FakeCur.log), 'revenue column added inside the existing top-selling query')
writes = [q for q in FakeCur.log if q.upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]
ok(writes == [], 'dashboard runs read-only SQL only (no INSERT/UPDATE/DELETE)')

print(f'\nTOTAL {PASS + FAIL}  PASS {PASS}  FAIL {FAIL}')
sys.exit(1 if FAIL else 0)
