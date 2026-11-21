"""v92.00 (was v87.43): version endpoint, old-server message and password reset script are present.
Static checks only (no MySQL). Run through tests/run_all.py."""
import os, sys
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def read(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
fails = []
def ok(c, m):
    print(('PASS ' if c else 'FAIL ') + m)
    if not c: fails.append(m)
sync = read('pharmacy/routes/sync_api.py'); cfg = read('config.py'); reset = read('reset_password.py')
ok("@app.route('/api/server/info')" in sync, 'version endpoint exists')
ok("APP_VERSION = '101.03'" in cfg, 'server version is 101.03')
ok('password_hash=%s WHERE user_id' in reset and 'bcrypt.hashpw' in reset, 'reset_password.py stores a bcrypt hash')
app_js = read('../Android/www/js/app.js') if os.path.exists(os.path.join(ROOT, '../Android/www/js/app.js')) else ''
if app_js:
    ok("var APP_VERSION = '101.03'" in app_js and '/api/server/info' in app_js, 'phone checks the server version')
if fails:
    sys.exit(1)
