"""Step 4 checks: DB-backed login lock, same timing for unknown users, input checks for users.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, re
sys.path.insert(0, ROOT); os_cwd = _os.getcwd(); _os.chdir(ROOT)

checkpw_calls = []
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'salt'
bc.hashpw = lambda p, s: b'h:' + p
def _checkpw(p, h):
    checkpw_calls.append(h)
    return h == b'h:' + p
bc.checkpw = _checkpw
sys.modules['bcrypt'] = bc

RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

class Cur:
    log = []
    attempts = {}     # fake login_attempts table
    users_known = True
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split()); self.p = p; Cur.log.append((self.sql, p))
        self.row = None
        if 'login_attempts' in self.sql:
            if self.sql.startswith('SELECT'):
                self.row = Cur.attempts.get(p[0])
            elif self.sql.startswith('INSERT INTO login_attempts'):
                Cur.attempts[p[0]] = {'fail_count': p[1], 'locked_until': p[2]}
            elif self.sql.startswith('DELETE FROM login_attempts'):
                Cur.attempts.pop(p[0], None)
    def fetchone(self):
        s = self.sql
        if 'login_attempts' in s: return self.row
        if 'information_schema' in s: return {'n': 1}
        if 'FROM users u JOIN roles' in s:
            return dict(user_id=1, full_name='Ahmed', password_hash='h:admin123', role_name='Admin') if Cur.users_known else None
        if 'SELECT password_hash FROM users' in s: return dict(password_hash='h:admin123')
        if 'SELECT user_id FROM users WHERE username' in s: return None
        if 'FROM roles WHERE role_id' in s: return dict(role_id=3)
        return {}
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
from pharmacy import core
A.app.config['TESTING'] = False
c = A.app.test_client()
def fresh_token():
    # a login (or failed login) can rotate the session, so always read a new token first
    r = c.get('/login')
    if r.status_code == 302:            # already logged in: a logged-in user is sent to the dashboard
        r = c.get('/dashboard')
    return re.search(r'name="csrf-token" content="([0-9a-f]+)"', r.get_data(as_text=True)).group(1)
def login(user, pw):
    return c.post('/login', data={'username': user, 'password': pw, 'csrf_token': fresh_token()})
tok = fresh_token()

# ---- lock key: hashed, case-insensitive, no raw IP/username ----
k1 = core._lock_key('10.0.0.5', 'Admin')
k2 = core._lock_key('10.0.0.5', 'admin')
ok(k1 == k2, 'lock key ignores username case')
ok('admin' not in k1 and '10.0.0.5' not in k1 and len(k1) == 64, 'lock key is a SHA-256 hash (no raw IP or name)')
ok(core._lock_key('10.0.0.6', 'admin') != k1, 'different IP -> different lock key')

# ---- lock lives in the table, survives a fresh start (state only in DB) ----
Cur.attempts.clear()
for i in range(4):
    c.post('/login', data={'username': 'admin', 'password': 'bad', 'csrf_token': tok})
ok(Cur.attempts and list(Cur.attempts.values())[0]['fail_count'] == 4, '4 wrong passwords stored in login_attempts')
r = c.post('/login', data={'username': 'admin', 'password': 'bad', 'csrf_token': tok})
ok(r.status_code == 429 or 'Login is locked' in r.get_data(as_text=True), '5th wrong password locks login')
r = c.post('/login', data={'username': 'admin', 'password': 'admin123', 'csrf_token': tok})
ok(r.status_code == 429, 'correct password still blocked while locked (lock read from DB)')

# ---- lock expires by itself ----
real_time = core.time.time
core.time.time = lambda: real_time() + 10 * 60          # 10 minutes later
try:
    ok(core._lock_left(core._lock_key('127.0.0.1', 'admin')) == 0, 'lock is gone after LOGIN_LOCK_MINUTES')
    r = login('admin', 'admin123')
    ok(r.status_code == 302, 'login works again after the lock expires')
finally:
    core.time.time = real_time

# ---- success clears the counter ----
Cur.attempts.clear()
login('admin', 'bad')
login('admin', 'admin123')
ok(not Cur.attempts, 'successful login deletes the failure counter')

# ---- timing: unknown user still runs one bcrypt check ----
Cur.users_known = False
checkpw_calls.clear()
login('ghost', 'whatever')
ok(len(checkpw_calls) == 1, 'unknown username still runs one bcrypt check (no fast reply)')
ok(checkpw_calls and checkpw_calls[0] == core.DUMMY_HASH, 'unknown username is checked against the dummy hash')
Cur.users_known = True

# ---- users: input checks happen before any INSERT ----
login('admin', 'admin123')
with c.session_transaction() as s:
    tok2 = s['_csrf']
def add(**kw):
    data = dict(csrf_token=tok2, full_name='Test User', username='staffone', password='Strong2026', role_id='3')
    data.update(kw)
    Cur.log.clear()
    c.post('/users/add', data=data)
    return any('INSERT INTO users' in q for q, _ in Cur.log)
ok(not add(username='a!'), 'bad username (symbols / too short) is rejected')
ok(not add(username='x' * 41), 'username longer than 40 is rejected')
ok(not add(full_name='x'), 'full name shorter than 2 characters is rejected')
ok(not add(role_id='abc'), 'non-numeric role is rejected')
Cur.users_known = True
ok(add(), 'valid user is created')

def set_time(start, end):
    Cur.log.clear()
    c.post(f'/users/set_time/2', data={'csrf_token': tok2, 'access_start_time': start, 'access_end_time': end})
    return any(q.startswith('UPDATE users SET access_start_time') for q, _ in Cur.log)
ok(not set_time('25:00', '06:00'), 'access time 25:00 is rejected')
ok(not set_time('9am', '06:00'), 'access time in wrong format is rejected')
ok(set_time('20:00', '06:00'), 'valid night-shift time 20:00-06:00 is saved')

# ---- schema: login_attempts table is created on start ----
src = open(_os.path.join(ROOT, 'pharmacy', 'core.py'), encoding='utf-8').read()
ok('CREATE TABLE IF NOT EXISTS login_attempts' in src, 'login_attempts table is in the schema setup')

_os.chdir(os_cwd)
failed = [n for n, good in RESULTS if not good]
for n, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed:
    sys.exit(1)
