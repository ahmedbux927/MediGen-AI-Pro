"""Step 5 checks: daily closing, udhaar list and WhatsApp reminder, phone rules, role access.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, re, datetime as dt
from decimal import Decimal as D
from urllib.parse import unquote, urlparse, parse_qs
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)

bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc

RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

from pharmacy.business_rules import normalize_pk_phone, udhaar_message, whatsapp_link

# ---- phone numbers ----
ok(normalize_pk_phone('0300-1234567') == '923001234567', 'phone 0300-1234567 -> 923001234567')
ok(normalize_pk_phone('+92 300 1234567') == '923001234567', 'phone +92 300 1234567 -> 923001234567')
ok(normalize_pk_phone('3001234567') == '923001234567', 'phone 3001234567 (no zero) -> 923001234567')
ok(normalize_pk_phone('0092 300 1234567') == '923001234567', 'phone 0092... -> 923001234567')
ok(normalize_pk_phone('') == '' and normalize_pk_phone(None) == '', 'empty phone -> no link')
ok(normalize_pk_phone('abc') == '' and normalize_pk_phone('0300123') == '', 'short or text phone -> no link')
ok(normalize_pk_phone('0123456789') == '', 'a 10-digit number starting with 0 is not forced into a mobile')
ok(normalize_pk_phone('0123-4567890') == '', 'landline-style 01x is not treated as mobile')

# ---- message and link ----
msg = udhaar_message('Sara Khan', 1234.5, 'City Medical')
ok('Rs. 1,234.50' in msg and 'City Medical' in msg and 'Sara' in msg, 'reminder has name, shop and amount with 2 decimals')
ok('Khan' not in msg.split('.')[0], 'reminder uses first name only')
ok(udhaar_message('', 10, 'S').startswith('Dear Sir/Madam'), 'empty name -> Sir/Madam')
link = whatsapp_link('0300-1234567', msg)
parsed = urlparse(link)
ok(parsed.netloc == 'wa.me' and parsed.path == '/923001234567', 'link goes to wa.me with the normalised number')
ok(unquote(parse_qs(parsed.query)['text'][0]) == msg, 'message round-trips through URL encoding (spaces, commas, dots)')
ok(whatsapp_link('abc', msg) == '', 'bad number -> empty link (no broken button)')

# ---- routes: mocked database ----
_LAST_ROLE = ['Admin']
class Cur:
    role = 'Admin'
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split()); self.p = p
    def fetchone(self):
        s = self.sql
        if 'FROM users u JOIN roles' in s:
            if self.p and isinstance(self.p[0], str):     # the login query remembers the role
                _LAST_ROLE[0] = 'Cashier' if self.p[0] == 'cashier' else 'Admin'
            role = _LAST_ROLE[0]
            return dict(user_id=1, full_name='Ahmed Ali', password_hash='h:admin123', role_name=role)
        if 'SELECT password_hash FROM users' in s: return dict(password_hash='h:admin123')
        if 'COUNT(*) AS n, IFNULL(SUM(total_amount)' in s:
            Cur.seen_day = self.p[0]
            return {'n': 3, 'gross': D('1500.00'), 'new_dues': D('200.00')}
        if 'SUM(si.quantity)' in s: return {'units': 12}
        if 'COUNT(*) AS n, IFNULL(SUM(refund_amount)' in s: return {'n': 1, 'refunds': D('50.00')}
        if 'information_schema' in s: return {'n': 1}
        return {}
    def fetchall(self):
        s = self.sql
        if 'GROUP BY method' in s: return [{'method': 'Cash', 'total': D('1000')}, {'method': 'Card', 'total': D('300')}]
        if 'GROUP BY c.customer_id' in s:
            Cur.dues_sql = s
            return [{'customer_id': 1, 'name': 'Sara Khan', 'contact_number': '0300-1234567', 'due': D('200.00'), 'oldest_sale': dt.date(2026, 10, 1)},
                    {'customer_id': 2, 'name': 'Bad Number', 'contact_number': 'none', 'due': D('75.5'), 'oldest_sale': None}]
        return []
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
A.app.config['TESTING'] = False

def client_as(user, pw='admin123'):
    c = A.app.test_client()
    tok = re.search(r'name="csrf-token" content="([0-9a-f]+)"', c.get('/login').get_data(as_text=True)).group(1)
    c.post('/login', data={'username': user, 'password': pw, 'csrf_token': tok})
    return c

admin = client_as('admin')
r = admin.get('/daily-closing?date=2026-10-10')
t = r.get_data(as_text=True)
ok(r.status_code == 200, 'closing page opens for Admin')
ok(Cur.seen_day == '2026-10-10', 'closing uses the date from the URL')
ok('Rs. 1,000.00' in t and 'Rs. 1,250.00' in t, 'closing shows money by method and net (1000 + 300 - 50 = 1250)')
ok('Rs. 50.00' in t and '12 units sold' in t, 'closing shows refunds and units sold')
r = admin.get('/daily-closing?date=not-a-date')
ok(r.status_code == 200 and Cur.seen_day == dt.date.today().isoformat(), 'bad date falls back to today')

r = admin.get('/customer-dues')
t = r.get_data(as_text=True)
ok(r.status_code == 200, 'udhaar page opens for Admin')
ok('wa.me/923001234567' in t, 'valid customer gets a WhatsApp button')
ok('No valid mobile number' in t, 'customer with a bad number gets a note, not a broken link')
ok('275.50' in t or '275.5' in t, 'udhaar page shows the total due (200 + 75.5)')
ok('JOIN customers c' in Cur.dues_sql and 'sales' in Cur.dues_sql, 'udhaar only counts sales with a named customer')

cashier = client_as('cashier', 'admin123')
for url in ('/daily-closing', '/customer-dues'):
    r = cashier.get(url)
    ok(r.status_code == 302 and r.headers['Location'].endswith('/dashboard'), f'Cashier cannot open {url}')

_nav = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read(); _hubs = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'hubs.py'), encoding='utf-8').read(); ok(("url_for('daily_closing')" in _nav or "'daily_closing'," in _hubs) and ("url_for('customer_dues')" in _nav or "'customer_dues'," in _hubs), 'nav links to closing and udhaar exist (sidebar or Finance hub)')

_os.chdir(_cwd)
failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS:
    print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed:
    sys.exit(1)
