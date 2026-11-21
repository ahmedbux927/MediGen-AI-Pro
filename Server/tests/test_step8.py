"""Step 8 checks: shared JavaScript (app.js), keyboard shortcuts on the sale page, base template guard.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, re, shutil, subprocess
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, rel), encoding='utf-8').read()

# ---- guard: base template must not lose its style block again (a truncated copy broke the look) ----
base = read('templates/base.html')
ok(len(base.splitlines()) > 150 and '{% block content %}' in base and 'css/app.css' in base,
   'base template is complete (theme linked, content block present)')
ok("js/app.js" in base and "url_for('static', filename='js/app.js')" in base, 'base template loads the shared app.js')

# ---- app.js content ----
js = read('static/js/app.js')
ok('MediGen.csrfToken' in js and "'X-CSRFToken'" in js, 'app.js sends the CSRF token on POST')
ok('textContent' in js and 'innerHTML' not in js, 'toast uses textContent (no HTML injection)')
ok('eval(' not in js and 'document.write' not in js, 'app.js has no eval or document.write')
ok('MediGen.shortcut' in js and 'MediGen.toast' in js, 'app.js exposes toast and shortcut helpers')
node = shutil.which('node') or ('/opt/node22/bin/node' if _os.path.exists('/opt/node22/bin/node') else None)
if node:
    r = subprocess.run([node, '--check', _os.path.join(ROOT, 'static', 'js', 'app.js')], capture_output=True, text=True)
    ok(r.returncode == 0, 'app.js passes a JavaScript syntax check')
else:
    ok(True, 'node not found: JavaScript syntax check skipped')

# ---- sale page shortcuts ----
sale = read('templates/new_sale.html')
ok("document.addEventListener('DOMContentLoaded'" in sale, 'sale shortcuts wait for the page (app.js loads after the page script)')
ok("MediGen.shortcut('F2'" in sale and "MediGen.shortcut('F3'" in sale and "MediGen.shortcut('F4'" in sale,
   'F2 scan box, F3 add item, F4 paid amount are set')
ok('Escape' in sale and 'scanMsg' in sale, 'Esc clears the scan message')
ok('<b>F2</b>' in sale, 'the screen shows the key hint')

# ---- served by Flask ----
class Cur:
    def execute(self, sql, p=None): self.sql = " ".join(sql.split())
    def fetchone(self): return {'n': 1} if 'information_schema' in self.sql else {}
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
c = A.app.test_client()
r = c.get('/static/js/app.js')
ok(r.status_code == 200 and b'MediGen' in r.data, 'app.js is served by the app (works offline, no CDN)')

_os.chdir(_cwd)
failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
