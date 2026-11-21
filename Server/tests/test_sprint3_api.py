"""Sprint 3 checks: API tokens, read-only REST API, service worker and manifest. Mock database. Run through tests/run_all.py."""
import os as _os, sys, types, json
from decimal import Decimal as D
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

from pharmacy.api_auth import hash_token, create_token, find_token, TOKEN_ROLES

GOOD_PHARM = 'mgk_pharmacist-token-for-tests'
GOOD_ADMIN = 'mgk_admin-token-for-tests'
TOKENS = {hash_token(GOOD_PHARM): {'token_id': 1, 'label': 'Phone', 'role': 'Pharmacist'},
          hash_token(GOOD_ADMIN): {'token_id': 2, 'label': 'Owner', 'role': 'Admin'}}

class Cur:
    def __init__(self, log): self.log = log; self.rows = []
    def execute(self, sql, p=None):
        self.sql = ' '.join(sql.split()); self.p = p or []; self.log.append((self.sql, self.p))
        self.rows = []
        if 'FROM api_tokens WHERE token_hash' in self.sql:
            row = TOKENS.get(self.p[0]); self.rows = [row] if row else []
        elif 'COUNT(*) AS total FROM medicines' in self.sql:
            self.rows = [{'total': 1}]
        elif 'FROM medicines m LEFT JOIN categories' in self.sql:
            row = {'medicine_id': 4, 'name': 'Panadol', 'category': 'Tablet', 'price': D('10.00'),
                   'stock': 30, 'reorder_level': 20, 'barcode': None}
            if 'm.cost_price' in self.sql:            # the real query adds cost_price only for Admin
                row['cost_price'] = D('5.50')
            self.rows = [row]
        elif 'WHERE m.quantity' in self.sql or 'stock_quantity <= reorder_level' in self.sql:
            self.rows = [{'name': 'Panadol', 'stock_quantity': 3, 'reorder_level': 20}]
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return list(self.rows)
    def close(self): pass
class Conn:
    def __init__(self): self.log = []; self.commits = 0
    def cursor(self): return Cur(self.log)
    def commit(self): self.commits += 1
    def rollback(self): pass
fake = Conn()
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = fake
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m

import pharmacy.core as core
import pharmacy.routes  # noqa: F401  registers every URL, as app.py does
core._schema_ready = True          # skip the schema check in this mock test
client = core.app.test_client()

# ---- token rules (pure) ----
ok(hash_token('abc') == hash_token('abc') and len(hash_token('abc')) == 64, 'token hash is a stable 64-character SHA-256')
ok(hash_token('abc') != hash_token('abd'), 'different tokens give different hashes')
ok(find_token(Cur([]), 'not-a-token') is None and find_token(Cur([]), '') is None, 'strings without the mgk_ prefix are rejected before the database')
ok(TOKEN_ROLES == ('Admin', 'Pharmacist'), 'tokens can only be Admin or Pharmacist (Cashier has no API)')
class Store:
    def __init__(self): self.params = None
    def execute(self, sql, p=None): self.params = p
raw = create_token(Store(), 'Phone', 'Pharmacist')
st = Store(); raw = create_token(st, 'Phone', 'Pharmacist')
ok(raw.startswith('mgk_') and len(raw) > 30, 'a long random token is created')
ok(raw not in st.params and hash_token(raw) in st.params, 'only the hash is stored, never the token itself')
try:
    create_token(Store(), 'x', 'Cashier'); bad = False
except ValueError:
    bad = True
ok(bad, 'a token for a Cashier is refused')

# ---- HTTP API ----
r = client.get('/api/v1/health')
ok(r.status_code == 200 and r.get_json()['ok'] is True, 'health check works without a token')
r = client.get('/api/v1/medicines')
ok(r.status_code == 401, 'medicines needs a token (401 without one)')
r = client.get('/api/v1/medicines', headers={'Authorization': 'Bearer mgk_wrong'})
ok(r.status_code == 401, 'a wrong token is refused')
r = client.get('/api/v1/medicines', headers={'Authorization': 'Bearer ' + GOOD_PHARM})
body = r.get_json()
ok(r.status_code == 200 and body['data'][0]['name'] == 'Panadol', 'pharmacist token reads the medicine list')
ok('cost_price' not in body['data'][0], 'pharmacist token does not get the cost price')
ok(body['meta'] == {'page': 1, 'per': 25, 'total': 1}, 'list has paging information')
r = client.get('/api/v1/medicines', headers={'Authorization': 'Bearer ' + GOOD_ADMIN})
ok('cost_price' in r.get_json()['data'][0], 'admin token also gets the cost price')
r = client.get('/api/v1/sales/summary', headers={'Authorization': 'Bearer ' + GOOD_PHARM})
ok(r.status_code == 403, 'sales summary is for the Admin token only (403 for pharmacist)')
r = client.get('/api/v1/stock/low', headers={'Authorization': 'Bearer ' + GOOD_PHARM})
ok(r.status_code == 200 and r.get_json()['data'][0]['stock'] == 3, 'low stock list works')
ok(fake.commits > 0, 'last_used is saved when a token is used')
ok('password' not in client.get('/api/v1/medicines', headers={'Authorization': 'Bearer ' + GOOD_ADMIN}).get_data(as_text=True).lower(), 'no password data in API output')
ok(not any(rule.rule.startswith('/api/v1/') and ('POST' in rule.methods or 'PUT' in rule.methods or 'DELETE' in rule.methods) for rule in core.app.url_map.iter_rules()), 'the API has no write routes (read-only)')

# ---- service worker and install manifest ----
r = client.get('/sw.js')
ok(r.status_code == 200 and r.headers.get('Service-Worker-Allowed') == '/', 'service worker is served from the site root')
ok('/static/' in open(_os.path.join(ROOT, 'static', 'js', 'sw.js'), encoding='utf-8').read(), 'service worker caches only static files')
sw = open(_os.path.join(ROOT, 'static', 'js', 'sw.js'), encoding='utf-8').read()
ok('req.method !== \'GET\'' in sw and 'every API response always comes from the server' in sw and 'PAGE_MAX_AGE_MS' in sw, 'service worker caches only static files and the sale page (24-hour limit)')
r = client.get('/manifest.webmanifest')
man = json.loads(r.get_data(as_text=True))
ok(r.status_code == 200 and 'manifest+json' in r.headers.get('Content-Type', ''), 'manifest is served with the right type')
ok(man['display'] == 'standalone' and man['start_url'] == '/dashboard' and len(man['icons']) == 2, 'manifest has standalone mode, start page and two icons')
ok(_os.path.exists(_os.path.join(ROOT, 'static', 'icons', 'icon-192.png')) and _os.path.exists(_os.path.join(ROOT, 'static', 'icons', 'icon-512.png')), 'both icon files exist')
base = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
ok('rel="manifest"' in base and "navigator.serviceWorker.register('/sw.js')" in base, 'pages link the manifest and register the service worker')
_os.chdir(_cwd)

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
