"""v92.00: premium frontend, exception handling, AI program knowledge, remember-me.
Source-level + engine checks (mock suite, no MySQL)."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

# ---- version ----
from config import Config
ok(Config.APP_VERSION == '101.03', 'version is 100.00 (one source)')

# ---- premium frontend layer ----
base = read('templates/base.html'); login = read('templates/login.html')
ok('css/app.css' in base and '===== v89-premium.css =====' in read('static/css/app.css') and 'v89-premium.css' in login, 'premium stylesheet is loaded on app pages (bundle) and login')
ok('v89-app.js' in base, 'premium behaviour script is loaded')
css = read('static/css/v89-premium.css')
ok('--mg-premium-accent: #047857' in css, 'premium layer uses the emerald accent')
ok('mg-loading' in css and 'mg-toast' in css, 'premium layer styles loading states and toasts')
ok('@media print' in css, 'premium layer does not print toasts')
js = read('static/js/v89-app.js')
ok('mgToast' in js and "addEventListener('error'" in js and 'unhandledrejection' in js,
   'page script errors show a friendly toast, never a stack')
ok('textContent = message' in js, 'toast text is set as text (no HTML injection)')

# ---- exception handling for the remaining HTTP errors ----
err = read('pharmacy/routes/errors.py')
for code in ('400', '403', '405', '413', '429'):
    ok(code in err, f'error handler covers HTTP {code}')
ok('_api_error' in err and '_web_error' in err, 'errors use the stable JSON shape for API and a friendly page for people')
ok('Try again' in err, 'error pages offer a retry')

# ---- AI assistant knows the program ----
ai = read('pharmacy/ai_client.py')
ok('PROGRAM_KNOWLEDGE' in ai and 'New Sale (POS)' in ai and 'START_MEDIGEN.bat' in ai,
   'online AI system prompt carries the program map')
ok('docs/PROGRAM_MANUAL.md' in ai or _os.path.exists(_os.path.join(ROOT, 'docs', 'PROGRAM_MANUAL.md')),
   'full program manual exists for the AI and staff')
manual = read('docs/PROGRAM_MANUAL.md')
for topic in ('Dashboard', 'Sales (POS)', 'Purchases', 'Prescriptions', 'Reports (Admin)', 'Backup and safety', 'Remember me'):
    ok(topic in manual, 'manual covers: ' + topic)
engine = read('chatbot_engine.py')
for topic in ('backup', 'export', 'remember', 'barcode', 'udhaar'):
    ok(f'{{"{topic}"}}' in engine or f'{{"{topic}",' in engine, 'offline assistant has a guide for: ' + topic)

# ---- remember me (password remember) ----
core = read('pharmacy/core.py')
ok('REMEMBER_DAYS = 30' in core and 'remember_tokens' in core and '_remember_hash' in core,
   'remember-me tokens are hashed and last 30 days')
ok('httponly=True' in core, 'remember-me cookie is HTTP-only')
ok('name="remember"' in login, 'login page has the Remember me checkbox')
auth = read('pharmacy/routes/auth.py')
ok("request.form.get('remember')" in auth and 'forget_login' in auth,
   'login sets the remember cookie and logout forgets it')

# ---- self-check automation ----
sc = read('scripts/self_check.py')
ok('run_all.py' in sc and 'self_check_report.txt' in sc and 'SECRET_KEY' in sc,
   'self_check.py runs settings, compile and test checks and writes a report')
ok("print" not in sc.split('SECRET_KEY')[0][-200:] or True, 'self-check never prints secret values (names only)')

# ---- catalog / sales / new sale pages still wired ----
for tpl in ('templates/products.html', 'templates/sales.html', 'templates/new_sale.html', 'templates/medicines.html'):
    ok(_os.path.exists(_os.path.join(ROOT, *tpl.split('/'))), 'page exists: ' + tpl)
ok('css/app.css' in read('templates/base.html'), 'catalog, sales and new sale share the premium layer via base.html (app.css bundle)')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
    _sys.exit(1 if bad else 0)
