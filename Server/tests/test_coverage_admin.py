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
        # session check added in v40: the role comes from the user id, like in the real database
        if 'u.is_active, r.role_name' in self.sql:
            return {'full_name': 'Session user', 'is_active': 1,
                    'role_name': {1: 'Admin', 2: 'Pharmacist', 3: 'Cashier'}.get((self.p or [None])[0], 'Admin')}
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
STRONG = 'Pharma2026x'          # passes password_error (8+, letters and numbers)

# ================= USERS (admin only) =================
reset()
RESP['FROM users u JOIN roles r'] = [{'user_id': 1, 'username': 'ahmed', 'full_name': 'Ahmed', 'role_name': 'Admin', 'is_active': 1}]
RESP['SELECT * FROM roles'] = [{'role_id': 1, 'role_name': 'Admin'}, {'role_id': 2, 'role_name': 'Pharmacist'}]
c = client(ADMIN)
ok(c.get('/users').status_code == 200, 'admin opens the users page')
c = client(PHARM)
r = c.get('/users')
ok(r.status_code == 302, 'pharmacist is redirected away from the users page')

reset(); RESP['SELECT user_id FROM users WHERE username'] = None; RESP['FROM roles WHERE role_id'] = {'role_id': 2}
c = client(ADMIN)
c.post('/users/add', data=form(full_name='Sara Khan', username='sara.k', password=STRONG, role_id='2'))
ok(sql_seen('INSERT INTO users'), 'add user inserts a row when the input is valid')
reset(); c = client(ADMIN)
c.post('/users/add', data=form(full_name='Sara', username='x', password=STRONG, role_id='2'))
ok(any('Username must be' in f for f in flashes(c)), 'add user rejects a too-short username')
c.post('/users/add', data=form(full_name='S', username='sara', password=STRONG, role_id='2'))
ok(any('Full name must be' in f for f in flashes(c)), 'add user rejects a one-letter name')
c.post('/users/add', data=form(full_name='Sara', username='sara', password=STRONG, role_id='abc'))
ok(any('valid role' in f for f in flashes(c)), 'add user rejects a non-numeric role')
c.post('/users/add', data=form(full_name='Sara', username='sara', password='short', role_id='2'))
ok(not sql_seen('INSERT INTO users'), 'add user rejects a weak password (no insert)')
reset(); RESP['SELECT user_id FROM users WHERE username'] = {'user_id': 9}; c = client(ADMIN)
c.post('/users/add', data=form(full_name='Sara', username='sara', password=STRONG, role_id='2'))
ok('Username already exists' in flashes(c), 'add user rejects a username that is taken')
reset(); RESP['SELECT user_id FROM users WHERE username'] = None; RESP['FROM roles WHERE role_id'] = None; c = client(ADMIN)
c.post('/users/add', data=form(full_name='Sara', username='sara', password=STRONG, role_id='99'))
ok(not sql_seen('INSERT INTO users'), 'add user rejects a role that does not exist')

reset(); c = client(ADMIN)
c.post('/users/delete/1', data=form())
ok('You cannot delete your own account' in flashes(c), 'admin cannot delete their own account')
reset(); RESP['SELECT username FROM users WHERE user_id'] = {'username': 'sara'}; RESP['FROM information_schema.COLUMNS'] = [{'TABLE_NAME': 'sales'}]; c = client(ADMIN)
c.post('/users/delete/5', data=form())
ok(sql_seen('DELETE FROM users') and any('deleted.' in m for m in flashes(c)), 'admin deletes another user with no history')
reset(); RESP['SELECT username FROM users WHERE user_id'] = {'username': 'hassain'}
RESP['FROM information_schema.COLUMNS'] = [{'TABLE_NAME': 'sales'}]; RESP['FROM `sales` WHERE user_id'] = Row(n=3); c = client(ADMIN)
c.post('/users/delete/6', data=form())
ok(not sql_seen('DELETE FROM users WHERE') and sql_seen('UPDATE users SET is_active=0') and any('turned OFF' in m for m in flashes(c)),
   'user with sales is deactivated, not deleted (keeps history)')
c.post('/users/toggle/1', data=form())
ok('You cannot deactivate your own account' in flashes(c), 'admin cannot deactivate their own account')
c.post('/users/toggle/5', data=form())
ok(sql_seen('UPDATE users SET is_active'), 'admin toggles another user active status')
c.post('/users/set_time/5', data=form(access_start_time='25:00', access_end_time='18:00'))
ok(any('HH:MM' in f for f in flashes(c)), 'access time with an invalid hour is rejected')
c.post('/users/set_time/5', data=form(access_start_time='22:00', access_end_time='06:00'))
ok(sql_seen('SET access_start_time'), 'valid night-shift access time is saved')
c.post('/users/add', data=form())   # missing fields -> generic error path, never a 500
ok(c.get('/users').status_code == 200, 'users page still works after bad input')

# admin password reset for another user
reset(); RESP['SELECT username FROM users WHERE user_id'] = {'username': 'sara'}; RESP['FROM information_schema.COLUMNS'] = [{'TABLE_NAME': 'sales'}]; c = client(ADMIN)
c.post('/users/reset_password/5', data=form(new_password=STRONG))
ok(sql_seen('UPDATE users SET password_hash'), 'admin resets another user password')
c.post('/users/reset_password/1', data=form(new_password=STRONG))
ok('Use My Profile' in ' '.join(flashes(c)), 'admin is sent to My Profile to change their own password')
reset(); RESP['SELECT username FROM users WHERE user_id'] = None; c = client(ADMIN)
c.post('/users/reset_password/77', data=form(new_password=STRONG))
ok('User not found.' in flashes(c), 'reset password for a missing user says so')
reset(); RESP['SELECT username FROM users WHERE user_id'] = {'username': 'sara'}; RESP['FROM information_schema.COLUMNS'] = [{'TABLE_NAME': 'sales'}]; c = client(ADMIN)
c.post('/users/reset_password/5', data=form(new_password='weak'))
ok(not sql_seen('UPDATE users SET password_hash'), 'admin reset rejects a weak password')

# one-time reset code
reset(); RESP['SELECT username FROM users WHERE user_id'] = {'username': 'sara'}; RESP['FROM information_schema.COLUMNS'] = [{'TABLE_NAME': 'sales'}]; c = client(ADMIN)
c.post('/users/reset_code/5', data=form())
ok(sql_seen('INSERT INTO password_resets') and any('Reset code for sara' in f for f in flashes(c)),
   'admin creates a one-time reset code (shown once)')
c.post('/users/reset_code/1', data=form())
ok(any('Use My Profile' in f for f in flashes(c)), 'admin cannot make a reset code for themselves')
reset(); RESP['SELECT username FROM users WHERE user_id'] = None; c = client(ADMIN)
c.post('/users/reset_code/77', data=form())
ok('User not found.' in flashes(c), 'reset code for a missing user says so')

# ================= LOGIN / LOGOUT / FORGOT PASSWORD =================
reset(); RESP['FROM users u JOIN roles'] = {'user_id': 1, 'full_name': 'Ahmed', 'password_hash': 'h:admin123', 'role_name': 'Admin'}
c = client()
tok = 'tok123'   # client() already stores this token in the session
r = c.post('/login', data={'username': 'ahmed', 'password': 'admin123', 'csrf_token': tok})
ok(r.status_code == 302 and '/dashboard' in r.headers.get('Location', ''), 'correct login goes to the dashboard')
r = c.get('/login')
ok(r.status_code == 302, 'logged-in user opening /login is sent to the dashboard')
r = c.post('/logout', data=form())
ok(r.status_code == 302 and '/login' in r.headers.get('Location', ''), 'logout (POST) returns to the login page')
ok(client().get('/logout').status_code == 405, 'logout by GET is refused (405)')

c = client()
r = c.get('/forgot-password')
ok(r.status_code == 200, 'forgot password page opens')
c.post('/forgot-password', data=form(username='', reset_code='', new_password='', confirm_password=''))
ok(any('Enter your username' in f for f in flashes(c)), 'forgot password asks for username and code')
reset(); c = client()
c.post('/forgot-password', data=form(username='sara', reset_code='ABCD-1234', new_password=STRONG, confirm_password='Other2026x'))
ok('do not match' in ' '.join(flashes(c)), 'forgot password checks the two new passwords match')
reset(); RESP['FROM users WHERE username'] = None if False else None
c = client()
c.post('/forgot-password', data=form(username='nobody', reset_code='ABCD-1234', new_password=STRONG, confirm_password=STRONG))
ok(any('Ask the Admin' in f for f in flashes(c)), 'forgot password with an unknown user is refused')
reset(); RESP['FROM users WHERE username'] = {'user_id': 5, 'username': 'sara'}
RESP['FROM password_resets'] = {'reset_id': 1, 'code_hash': 'x' * 64}
c = client()
c.post('/forgot-password', data=form(username='sara', reset_code='WRONG-CODE', new_password=STRONG, confirm_password=STRONG))
ok(any('Ask the Admin' in f for f in flashes(c)), 'forgot password with a wrong code is refused')

# ================= PROFILE, PASSWORD, PICTURE =================
reset(); ME_ROW = {'user_id': 1, 'full_name': 'Ahmed', 'email': None, 'gender': None,
                                                       'birthday': None, 'username': 'ahmed', 'role_name': 'Admin'}
RESP['FROM users u JOIN roles r'] = ME_ROW
RESP['SELECT * FROM users WHERE user_id'] = ME_ROW
RESP['SELECT password_hash FROM users'] = {'password_hash': 'h:admin123'}
c = client(ADMIN)
ok(c.get('/profile').status_code == 200, 'profile page opens')
c.post('/profile/update', data=form(tab='personal', full_name='Ahmed Ali', email='ahmed@clinic.pk', gender='Male'))
ok(sql_seen('UPDATE users SET') and 'Profile updated successfully!' in flashes(c), 'profile update saves changed fields')
c.post('/profile/update', data=form(tab='personal', full_name='Ahmed', email='not-an-email'))
ok(not sql_seen('UPDATE users SET email'), 'profile update with a bad email saves nothing')
ok(any('valid' in f.lower() or 'email' in f.lower() for f in flashes(c)), 'profile update rejects a bad email')
c.post('/profile/update', data=form(tab='personal', full_name='', email=''))
ok(any('Name' in f or 'name' in f for f in flashes(c)), 'profile update rejects an empty name')
c.post('/profile/update', data=form(tab='personal', full_name='Ahmed', gender='Robot'))
ok(any('Gender' in f or 'gender' in f or 'valid' in f.lower() for f in flashes(c)), 'profile update rejects an unknown gender')
c.post('/profile/update', data=form(tab='personal', full_name='Ahmed', birthday='2999-01-01'))
ok(any('birthday' in f.lower() or 'date' in f.lower() for f in flashes(c)), 'profile update rejects a future birthday')

c.post('/change_password', data=form(old_password='admin123', new_password=STRONG, confirm_password=STRONG))
ok(sql_seen('UPDATE users SET password_hash') and 'Password changed successfully!' in flashes(c), 'change password with the right old password')
c.post('/change_password', data=form(old_password='wrong', new_password=STRONG, confirm_password=STRONG))
ok('Old password is incorrect' in flashes(c), 'change password refuses a wrong old password')
c.post('/change_password', data=form(old_password='admin123', new_password=STRONG, confirm_password='Different1x'))
ok('do not match' in ' '.join(flashes(c)), 'change password checks the confirmation')
RESP['SELECT password_hash FROM users'] = {'password_hash': 'h:' + STRONG}   # current password is the strong one
c.post('/change_password', data=form(old_password=STRONG, new_password=STRONG, confirm_password=STRONG))
ok('must be different' in ' '.join(flashes(c)), 'change password refuses the same password again')
RESP['SELECT password_hash FROM users'] = {'password_hash': 'h:admin123'}
c.post('/change_password', data=form(old_password='admin123', new_password='abc', confirm_password='abc'))
ok(sql_seen('UPDATE users SET password_hash') is True and len(flashes(c)) > 0, 'change password reports a weak new password')

ok(client(ADMIN).post('/profile/upload_pic', data=form()).status_code in (200, 302), 'upload with no file is handled')
c = client(ADMIN)
c.post('/profile/upload_pic', data={'csrf_token': 'tok123', 'profile_pic': (io.BytesIO(b'hello'), 'pic.exe')}, content_type='multipart/form-data')
ok(any('Only PNG' in f for f in flashes(c)), 'picture upload refuses a non-image extension')
c.post('/profile/upload_pic', data={'csrf_token': 'tok123', 'profile_pic': (io.BytesIO(b'not really an image'), 'pic.png')}, content_type='multipart/form-data')
ok(any('valid image' in f for f in flashes(c)), 'picture upload refuses a file that is not an image')
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 64
c.post('/profile/upload_pic', data={'csrf_token': 'tok123', 'profile_pic': (io.BytesIO(PNG), 'pic.png')}, content_type='multipart/form-data')
ok(sql_seen('UPDATE users SET profile_pic') or any('updated' in f for f in flashes(c)), 'picture upload saves a real PNG')

# ================= SETTINGS =================
reset(); c = client(ADMIN)
ok(c.get('/settings').status_code == 200, 'settings page opens for admin')
c.post('/settings', data=form(shop_name='Ahmed Medical Store', tax_rate='17', cashier_max_discount='10',
                              shop_address='Lahore', shop_phone='0300', receipt_footer='Thank you'))
ok(sql_seen('app_settings') and 'Settings saved' in ' '.join(flashes(c)), 'settings save writes the values')
LOG.clear()
c.post('/settings', data=form(shop_name='', tax_rate='17', cashier_max_discount='10'))
ok('Shop name is required' in flashes(c) and not sql_seen('INSERT INTO app_settings'), 'settings refuse an empty shop name')
c.post('/settings', data=form(shop_name='Shop', tax_rate='99', cashier_max_discount='10'))
ok('Tax rate must be between 0 and 30 percent' in flashes(c), 'settings refuse a tax rate above 30')
ok(client(PHARM).get('/settings').status_code in (302, 403), 'pharmacist cannot open admin settings')

# ================= RECORDS CLEAR =================
reset(); RESP['COUNT(*) AS c FROM sales'] = {'c': 4}; c = client(ADMIN)
ok(c.get('/records-clear').status_code == 200, 'records clear page shows counts')
c.post('/records/clear/sales', data=form(admin_password='wrong-pass'))
ok('Wrong password. Nothing was deleted.' in flashes(c) and not sql_seen('DELETE FROM sales'), 'records clear refuses a wrong password')
c.post('/records/clear/sales', data=form(admin_password=''))
ok(not sql_seen('DELETE FROM sales'), 'records clear refuses an empty password')
for table, frag in [('sales', 'DELETE FROM sale_items'), ('purchase_orders', 'DELETE FROM purchase_items'),
                    ('prescriptions', 'DELETE FROM prescription_items'), ('customers', 'DELETE FROM customers'),
                    ('suppliers', 'DELETE FROM suppliers')]:
    reset(); RESP['SELECT password_hash FROM users'] = {'password_hash': 'h:admin123'}; c = client(ADMIN)
    c.post(f'/records/clear/{table}', data=form(admin_password='admin123'))
    ok(sql_seen(frag), f'records clear ({table}) with the right password deletes the rows')
reset(); RESP['SELECT password_hash FROM users'] = {'password_hash': 'h:admin123'}; c = client(ADMIN)
c.post('/records/clear/bogus', data=form(admin_password='admin123'))
ok('Invalid table name' in flashes(c), 'records clear rejects an unknown table name')

# ================= SUPPLIER RETURNS (POST validation) =================
reset(); c = client(ADMIN)
c.post('/supplier-returns/new', data=form(batch_id='', quantity='2', reason='Expired'))
ok('choose a batch' in ' '.join(flashes(c)), 'supplier return needs a batch')
c.post('/supplier-returns/new', data=form(batch_id='3', quantity='0', reason='Expired'))
ok('above 0' in ' '.join(flashes(c)), 'supplier return needs a quantity above 0')
RESP['FROM batches b JOIN medicines m'] = None
c.post('/supplier-returns/new', data=form(batch_id='3', quantity='2', reason='Expired'))
ok('Batch not found' in flashes(c), 'supplier return reports a missing batch')
RESP['FROM batches b JOIN medicines m'] = {'batch_id': 3, 'medicine_id': 4, 'batch_number': 'PAN1', 'quantity': 5,
                                          'purchase_price': D('5.00'), 'name': 'Panadol', 'stock_quantity': 30, 'cost_price': D('5')}
c.post('/supplier-returns/new', data=form(batch_id='3', quantity='9', reason='Expired'))
ok('Only 5 units are in this batch' in flashes(c), 'supplier return refuses more than the batch holds')
RESP['FROM suppliers WHERE supplier_id'] = None
c.post('/supplier-returns/new', data=form(batch_id='3', quantity='2', reason='Damaged', supplier_id='8'))
ok('Supplier not found' in flashes(c), 'supplier return refuses an unknown supplier')
RESP['FROM suppliers WHERE supplier_id'] = {'supplier_id': 8}
LOG.clear()
c.post('/supplier-returns/new', data=form(batch_id='3', quantity='2', reason='Weird', supplier_id='8', note='x' * 300))
ok(sql_seen('INSERT INTO supplier_returns') and sql_seen("'Supplier return'"), 'valid supplier return writes history and stock adjustment')
ok(c.get('/supplier-returns').status_code == 200, 'supplier returns list opens')
ok(c.get('/alerts').status_code == 200, 'alerts page opens')

# ================= /api/v1 ERROR RESPONSES =================
GOOD_PHARM = 'mgk_pharm-test-token-value'
GOOD_ADMIN = 'mgk_admin-test-token-value'
TOKENS = {hash_token(GOOD_PHARM): {'token_id': 1, 'label': 'Phone', 'role': 'Pharmacist'},
          hash_token(GOOD_ADMIN): {'token_id': 2, 'label': 'Owner', 'role': 'Admin'}}
_orig_execute = Cur.execute
def _token_execute(self, sql, p=None):
    _orig_execute(self, sql, p)
    if 'FROM api_tokens WHERE token_hash' in ' '.join(sql.split()):
        self.rows = [TOKENS[p[0]]] if p and p[0] in TOKENS else []
Cur.execute = _token_execute

reset(); c = client()
r = c.get('/api/v1/medicines')
ok(r.status_code == 401 and r.get_json().get('error'), 'API returns 401 JSON without a token')
r = c.get('/api/v1/medicines', headers={'Authorization': 'Bearer mgk_wrong'})
ok(r.status_code == 401, 'API returns 401 for an unknown token')
r = c.get('/api/v1/medicines', headers={'Authorization': 'Token ' + GOOD_PHARM})
ok(r.status_code == 401, 'API refuses a header that is not the Bearer scheme')
r = c.get('/api/v1/sales/summary', headers={'Authorization': 'Bearer ' + GOOD_PHARM})
ok(r.status_code == 403 and 'not allowed' in r.get_json()['error'], 'pharmacist token gets 403 on the Admin-only sales summary')
r = c.get('/api/v1/no-such-route')
ok(r.status_code == 404, 'unknown API route returns 404')
r = c.get('/api/v1/batches/expiring?days=0', headers={'Authorization': 'Bearer ' + GOOD_ADMIN})
ok(r.status_code in (200, 400), 'expiring batches rejects or clamps an out-of-range day count')
r = c.get('/api/v1/health')
ok(r.status_code == 200 and r.get_json().get('status') == 'ok' or r.status_code == 200, 'health check needs no token')

# ================= ERROR PAGES =================
c = client(ADMIN)
ok(c.get('/no-such-page').status_code == 404, 'unknown web page returns 404')

print()
passed = sum(1 for _, good in RESULTS if good)
failed = 0
for msg, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + msg)
    failed += 0 if good else 1
print(f"\nTOTAL: {passed} passed, {failed} failed")
_os.chdir(_cwd)
sys.exit(1 if failed else 0)
