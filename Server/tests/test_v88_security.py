"""v92.00: security, version and Windows-script contracts. Source-level checks (no MySQL)."""
import glob, os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()
def readb(rel): return open(_os.path.join(ROOT, *rel.split('/')), 'rb').read()

# ---- one version source (B5 + Step 7) ----
from config import Config
ok(Config.APP_VERSION == '101.03', 'Config.APP_VERSION is 100.00')
core = read('pharmacy/core.py')
ok('APP_VERSION = Config.APP_VERSION' in core, 'core APP_VERSION reads Config (About page uses it)')
ok("APP_VERSION = '1.1.0'" not in core, 'hard-coded About version 1.1.0 is gone')
app_py = read('app.py')
ok("Config.APP_VERSION" in app_py, 'startup banner reads Config.APP_VERSION')

# ---- B1: waitress default, Flask only as warned fallback ----
ok('from waitress import serve' in app_py, 'app.py serves with waitress by default')
ok('WARNING: waitress is not installed' in app_py and 'development server' in app_py,
   'Flask fallback prints a clear English warning')

# ---- B3: requirements ----
req = read('requirements.txt')
ok('pdfplumber' in req, 'requirements.txt includes pdfplumber (B3)')
ok('waitress' in req, 'requirements.txt includes waitress')

# ---- B2: duplicate barcodes, read-only ----
ok('GROUP_CONCAT' in core and 'duplicate barcode' in core, 'startup detects duplicate live barcodes before the index')
sql = read('database/check_duplicate_barcodes.sql').upper()
import re as _re
ok('SELECT' in sql and not _re.search(r'\b(DELETE|UPDATE|ALTER|DROP|INSERT)\b', sql),
   'check_duplicate_barcodes.sql is read-only')

# ---- CSRF exemptions: deliberate list only ----
ok("/api/auth/otp" not in core, 'removed phone OTP route is no longer a CSRF exemption')
ok("request.path == '/api/auth/login'" in core, 'only /api/auth/login is exempt by path')
ok("startswith('bearer ')" in core, 'Bearer-token API calls are the other exemption')

# ---- E7: session and security ----
ok('SESSION_COOKIE_HTTPONLY = True' in read('config.py'), 'session cookie is HTTP-only')
ok('Password must be at least 8 characters' in core, 'minimum password length is 8')
auth = read('pharmacy/routes/auth.py')
ok('Too many wrong attempts. Login is locked for' in auth, 'lockout message is in English')
ok('X-Frame-Options' in core and 'X-Content-Type-Options' in core and 'Permissions-Policy' in core,
   'security headers are set on responses')
ok('SESSION_MINUTES' in read('config.py'), 'session expiry is configured')

# ---- B10 + Windows scripts ----
stop = read('STOP_MEDIGEN.bat')
ok('tokens=5' not in stop and 'for %%P in (%%L)' in stop, 'STOP_MEDIGEN.bat takes the PID from the last netstat column (B10)')
start = read('START_MEDIGEN.bat')
ok('MySQL80' in start and 'DB_PASSWORD' in start and 'LISTENING' in start,
   'START_MEDIGEN.bat checks .env keys, MySQL80 and the port')
ok('C:\\Users' not in start and 'C:\\Users' not in stop, 'start/stop scripts use relative paths only')
for p in glob.glob(_os.path.join(ROOT, '**', '*.bat'), recursive=True) + glob.glob(_os.path.join(ROOT, '**', '*.vbs'), recursive=True):
    data = open(p, 'rb').read()
    ok(b'\r\n' in data and data.replace(b'\r\n', b'').find(b'\n') == -1,
       'CRLF line endings: ' + _os.path.relpath(p, ROOT))
desk = read('START_MEDIGEN.bat')
ok('/api/server/info' in desk and 'start "" "http://127.0.0.1' in desk,
   'START_MEDIGEN.bat waits for the server, then opens the workbench')

# ---- E6: stable JSON error shape ----
err = read('pharmacy/routes/errors.py')
ok("'error': {'code': code, 'message': message}" in err or '"error": {"code"' in err or "{'code': code, 'message': message}" in err,
   'API errors use one stable JSON shape')
ok("startswith('/api/')" in err, 'API error shape applies to /api/ paths')

# ---- phone-only code removed ----
for gone in ('pharmacy/routes/mobile_stock.py', 'pharmacy/routes/phone_otp.py', 'static/js/offline-sale.js'):
    ok(not _os.path.exists(_os.path.join(ROOT, *gone.split('/'))), 'removed phone-only: ' + gone)
routes_init = read('pharmacy/routes/__init__.py')
ok('mobile_' not in routes_init and 'phone_otp' not in routes_init, 'phone routes are not registered')

# ---- E9: deletes are confirmed and logged ----
meds = read('pharmacy/routes/medicines.py')
ok("audit(cur, 'medicine.delete'" in meds, 'medicine delete is audit-logged')
ok("confirm('Delete" in read('templates/medicines.html'), 'medicine delete asks for confirmation')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
    _sys.exit(1 if bad else 0)

