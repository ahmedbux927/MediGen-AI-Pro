"""Profile and Settings: tabs, password change (audited, can return to Settings), About info, activity."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
import types
from datetime import datetime
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b''; bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
_sys.modules['bcrypt'] = bc
class Row(dict):
    def __missing__(self, key): return 0
USER = Row(user_id=1, full_name='Ahmed Ali', username='admin', role_name='Admin', gender='Male', email='a@x.com',
           phone='0300', birthday=None, language='Urdu', home_address='Sukkur', work_address='', other_address='',
           about='Pharmacist', position='Manager', projects='', license_info='PH-1', experience='', recommendations='',
           volunteer='', honors='', awards='', causes='', services='', profile_pic=None, is_active=1,
           access_start_time='08:00:00', access_end_time='22:00:00', password_hash='h:admin123')
AUDIT_ROWS = [dict(created_at=datetime(2026, 10, 13, 9, 0), action='login.success', details='', status='ok', entity=None, entity_id=None, request_id='r1')]
LOG = []
class Cur:
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split()); self.p = p; LOG.append((self.sql, p))
    def fetchone(self):
        s = self.sql
        if 'information_schema' in s: return Row(n=1)
        if s.startswith('SELECT u.*, r.role_name'): return USER
        if s.startswith('SELECT MAX(created_at)'): return Row(last_login=datetime(2026, 10, 13, 9, 0))
        if s.startswith('SELECT password_hash'): return USER
        if s.startswith('SELECT * FROM users WHERE user_id'): return USER
        if s.startswith('SELECT VERSION()'): return Row(v='8.0.46')
        return Row()
    def fetchall(self):
        if self.sql.startswith('SELECT created_at, action'): return AUDIT_ROWS
        return []
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
        s.update(user_id=1, user_name='Ahmed Ali', role=role); s['_csrf'] = 't'
    return c
F = {'csrf_token': 't'}
c = login()
h = c.get('/profile').get_data(as_text=True)
ok(c.get('/profile').status_code == 200 and 'Personal information' in h, 'profile page opens')
ok('id="personal"' in h and 'id="about"' in h and 'id="security"' in h and 'id="activity"' in h, 'profile has Personal, About, Security and Activity tabs')
ok('login.success' in h and 'Last login' in h, 'profile shows recent activity and last login')
ok('name="old_password"' in h and 'name="new_password"' in h and 'minlength="8"' in h, 'profile password form (min 8 characters)')
ok('value="Ahmed Ali"' in h and 'name="license_info"' in h, 'profile personal fields are filled from the database')

st = c.get('/settings').get_data(as_text=True)
ok('data-tab="security"' in st and 'data-tab="about"' in st and 'data-tab="money"' in st, 'settings has Shop, Money rules, Security and About tabs')
ok('name="next" value="settings"' in st, 'settings password form returns to Settings')
ok('Version' in st and '92.00' in st and 'Audit log' not in st, 'About tab shows version from Config.APP_VERSION (v92.00: B5, no audit tile)')
ok('MySQL 8.0.46' in st, 'About tab shows the MySQL version')
_ab = c.get('/settings?tab=about').get_data(as_text=True)
ok('class="pf-pane on" id="pane-about"' in _ab and 'data-tab="about" type="button"' in _ab, 'settings opens on the requested tab (?tab=about)')

LOG.clear()
r = c.post('/change_password', data={**F, 'old_password': 'admin123', 'new_password': 'Newpass2026', 'confirm_password': 'Newpass2026', 'next': 'settings'})
ok(r.status_code == 302 and r.headers['Location'].endswith('/settings'), 'password change from Settings returns to Settings')
ok(any(q.startswith('INSERT INTO audit_log') and p and p[2] == 'security.password_changed' for q, p in LOG), 'password change is audited (no password in the log)')
ok(not any(p and 'Newpass2026' in str(p) and q.startswith('INSERT INTO audit_log') for q, p in LOG), 'the new password is never written to the audit log')
LOG.clear()
r = c.post('/change_password', data={**F, 'old_password': 'wrong', 'new_password': 'Newpass2026', 'confirm_password': 'Newpass2026'})
ok(r.headers['Location'].endswith('/profile') and any(p and p[2] == 'security.password_denied' for q, p in LOG if q.startswith('INSERT INTO audit_log')), 'wrong current password -> denied and audited, returns to Profile')
LOG.clear()
r = c.post('/change_password', data={**F, 'old_password': 'admin123', 'new_password': 'weak', 'confirm_password': 'weak'})
ok(not any(q.startswith('UPDATE users SET password_hash') for q, _ in LOG), 'weak new password refused, nothing changed')
r = c.post('/change_password', data={**F, 'old_password': 'admin123', 'new_password': 'Newpass2026', 'confirm_password': 'Other2026'})
ok(not any(q.startswith('UPDATE users SET password_hash') for q, _ in LOG), 'mismatched confirmation refused')
LOG.clear()
c.post('/profile/update', data={**F, 'full_name': 'Ahmed Khan', 'gender': 'Male', 'email': 'a@x.com', 'phone': '0300', 'about': 'x'})
ok(any(q.startswith('INSERT INTO audit_log') and p and p[2] == 'profile.update' for q, p in LOG), 'profile update is audited')
ok(c.get('/profile/update').status_code == 405 or c.get('/profile/update').status_code == 302, 'profile update is POST only')
bad = login('Cashier').get('/settings')
ok(bad.status_code == 302, 'Cashier cannot open Settings (Admin only)')
ok(login('Cashier').get('/profile').status_code == 200, 'Cashier can open their own profile')
ok(login('Cashier').get('/profile').get_data(as_text=True).count('name="old_password"') == 1, 'Cashier profile has its own password change')
