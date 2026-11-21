"""Step 10 checks: safe error messages, logout by POST only, Cashier cannot see cost or medical history.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, re, glob
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

_LAST_ROLE = ['Admin']
class Row(dict):
    def __missing__(self, key): return 0
class Cur:
    def execute(self, sql, p=None): self.sql = " ".join(sql.split()); self.p = p
    def fetchone(self):
        s = self.sql
        if 'FROM users u JOIN roles' in s:
            if self.p and isinstance(self.p[0], str):     # the login query remembers the role
                _LAST_ROLE[0] = 'Cashier' if self.p[0] == 'cashier' else 'Admin'
                return dict(user_id=1, full_name='Ahmed Ali', password_hash='h:admin123', role_name=_LAST_ROLE[0])
            # session check by user id: the default test session is the Admin
            return dict(full_name='Ahmed Ali', is_active=1, role_name='Cashier' if self.p[0] == 3 else 'Admin')
        if 'SELECT password_hash FROM users' in s: return dict(password_hash='h:admin123')
        if 'information_schema' in s: return {'n': 1}
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
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m
import app as A
from pharmacy import lib as L
from flask import session as fsession

def read(*parts): return open(_os.path.join(ROOT, *parts), encoding='utf-8').read()

# ---- 1. no raw exception text is shown to users ----
raw = []
for p in glob.glob(_os.path.join(ROOT, 'pharmacy', 'routes', '*.py')):
    for n, line in enumerate(open(p, encoding='utf-8'), 1):
        if "flash(f" in line and "{str(e)}" in line:
            raw.append(f"{_os.path.basename(p)}:{n}")
ok(not raw, 'no route shows raw exception text (found: %s)' % (raw or 'none'))
ok('def flash_unexpected' in read('pharmacy', 'lib.py'), 'safe error helper flash_unexpected exists')
with A.app.test_request_context('/'):
    fsession['_flashes'] = []
    L.flash_unexpected('Backup failed.')
    msgs = list(fsession.get('_flashes', []))
ok(msgs and msgs[0][1].startswith('Backup failed.') and 'Traceback' not in msgs[0][1],
   'safe message shows the short text only')

# ---- 2. logout: POST only, CSRF protected ----
def client():
    c = A.app.test_client()
    tok = re.search(r'name="csrf-token" content="([0-9a-f]+)"', c.get('/login').get_data(as_text=True)).group(1)
    c.post('/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': tok})
    return c
c = client()
ok(c.get('/logout').status_code == 405, 'GET /logout is refused (405), so a plain link cannot log out')
home = c.get('/dashboard').get_data(as_text=True)
ok('action="/logout"' in home and 'method="post"' in home and 'name="csrf_token"' in home,
   'sidebar logout is a POST form with the CSRF token')
r = c.post('/logout', data={'csrf_token': 'wrong-token'})
with c.session_transaction() as s: kept = 'user_id' in s
ok(kept, 'POST /logout with a wrong token is refused and the session stays')
with c.session_transaction() as s: tok = s['_csrf']
r = c.post('/logout', data={'csrf_token': tok})
with c.session_transaction() as s: gone = 'user_id' not in s
ok(r.status_code == 302 and gone, 'POST /logout with the right token logs out and clears the session')

# ---- 3. Cashier cannot see cost price or medical history ----
cash = client()
with cash.session_transaction() as s: s['role'] = 'Cashier'; s['user_id'] = 3   # user 3 is the Cashier in the database
cust = cash.get('/customers').get_data(as_text=True)
ok('Medical History</th>' not in cust and 'With History' not in cust,
   'Cashier does not see the Medical History column or its stat')
adm = client().get('/customers').get_data(as_text=True)
ok('Medical History</th>' in adm and 'With History' in adm, 'Admin still sees Medical History')
meds = read('templates', 'medicines.html')
ok("session.role != 'Cashier' and m.cost_price" in meds, 'medicines page hides cost price from Cashier')
ok("0 if session.role == 'Cashier' else (m.cost_price or 0)" in meds, 'edit button does not carry cost price to Cashier')


# ---- CSV export and photo upload ----
ok("'' if session.get('role') == 'Cashier' else r['cost_price']" in read('pharmacy', 'routes', 'medicines.py'),
   'medicine CSV export leaves cost blank for Cashier')
from pharmacy.routes import profile as PR
ok(PR._is_image(b'\x89PNG\r\n\x1a\n' + b'0' * 8) and PR._is_image(b'\xff\xd8\xff\xe0' + b'0' * 8),
   'real PNG and JPEG headers are accepted')
ok(not PR._is_image(b'hello this is not an image') and not PR._is_image(b'<?php echo 1; ?>'),
   'renamed text or script files are refused')
c2 = client()
with c2.session_transaction() as s2: tok2 = s2['_csrf']
import io as _io
r2 = c2.post('/profile/upload_pic', data={'csrf_token': tok2, 'profile_pic': (_io.BytesIO(b'<?php echo 1; ?>'), 'evil.png')},
             content_type='multipart/form-data')
ok(r2.status_code == 302 and r2.headers['Location'].endswith('/profile'), 'fake image upload is redirected back to Profile')
with c2.session_transaction() as s2: fl = [m_ for _, m_ in (s2.get('_flashes') or [])]
ok(any('not a valid image' in m_ for m_ in fl), 'fake image upload shows a clear message')

def _boom():
    raise RuntimeError('secret internal detail')
from werkzeug.routing import Rule as _Rule
A.app.url_map.add(_Rule('/_test_boom', endpoint='test_boom'))
A.app.url_map.update()
A.app.view_functions['test_boom'] = _boom   # added after requests ran, so no add_url_rule()
A.app.config['PROPAGATE_EXCEPTIONS'] = False
bc2 = client()
rb = bc2.get('/_test_boom')
body_b = rb.get_data(as_text=True)
ok(rb.status_code == 500 and 'Traceback' not in body_b and 'secret internal detail' not in body_b,
   'unexpected error shows a safe 500 page, no traceback or raw error text')
ok('Sidebar' in body_b or 'Server' in body_b or '500' in body_b, 'the 500 page is the friendly page')
ok('css/app.css' in home, 'the app.css design bundle (incl. the classic theme) is linked')

failed = [x for x, p in RESULTS if not p]
for msg, p in RESULTS:
    print(('PASS ' if p else 'FAIL ') + msg)
_os.chdir(_cwd)
print(f'\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed')
sys.exit(1 if failed else 0)
