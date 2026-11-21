"""Frontend checks: mobile menu, themed error pages, login page, and every template compiles."""
import os as _os, sys as _sys, re as _re, glob as _glob
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
import types
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b''; bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
_sys.modules['bcrypt'] = bc
from datetime import datetime
class Row(dict):
    def __missing__(self, key): return 0
class Cur:
    def execute(self, sql, p=None): self.sql = " ".join(sql.split())
    def fetchone(self):
        if 'information_schema' in self.sql: return Row(n=1)
        return Row()
    def fetchall(self): return []
    def close(self): pass
class Conn:
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): pass
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = Conn()
m.MySQL = MySQL; _sys.modules['flask_mysqldb'] = m
import app as A
A.app.template_folder = ROOT + '/templates'
ok = lambda c, msg: print(('PASS ' if c else 'FAIL ') + msg)

def login(role='Admin'):
    c = A.app.test_client(); c.get('/login')
    with c.session_transaction() as s:
        s.update(user_id=1, user_name='Ahmed', role=role); s['_csrf'] = 't'
    return c

c = login()
h = c.get('/dashboard').get_data(as_text=True)
ok('id="menuToggle"' in h and 'id="menuBackdrop"' in h, 'logged-in pages have the mobile menu button')
_css = open(_os.path.join(ROOT, 'static', 'css', 'classic.css'), encoding='utf-8').read()   # styles live in the CSS file since Step 7
ok('translateX(-105%)' in _css and '.sidebar.open' in _css, 'sidebar slides in on phones (off-canvas CSS)')
ok('if (!sb || !bd) return;' in h, 'menu script is guarded for pages without a sidebar')
lg = A.app.test_client().get('/login').get_data(as_text=True)
ok('id="sidebar"' not in lg and 'Login' in lg, 'login page: no sidebar, login form present')
r = c.get('/no-such-page'); e = r.get_data(as_text=True)
ok(r.status_code == 404 and 'Page not found' in e and 'Back to Dashboard' in e, '404 page is themed and has a way back')
ok('Admin details' not in e, '404 page never shows technical details')
c_cash = login('Cashier')
ok('Audit Log' not in c_cash.get('/dashboard').get_data(as_text=True), 'Cashier does not see Admin-only menu items')
bad = []
for p in _glob.glob(ROOT + '/templates/*.html'):
    try:
        A.app.jinja_env.get_template(_os.path.basename(p))
    except Exception as ex:
        bad.append((_os.path.basename(p), str(ex)[:60]))
ok(not bad, 'every template compiles' + ('' if not bad else f' - problems: {bad}'))
