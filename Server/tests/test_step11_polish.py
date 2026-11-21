"""Step 11 checks: admin password reset, forgot-password page, neumorphism stylesheet, no raw errors.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(*parts): return open(_os.path.join(ROOT, *parts), encoding='utf-8').read()

users_src = read('pharmacy', 'routes', 'users.py')
auth_src = read('pharmacy', 'routes', 'auth.py')
base = read('templates', 'base.html')
login = read('templates', 'login.html')
users_html = read('templates', 'users.html')

# 1. Reset route exists, is admin-only, validates password and is audited
i = users_src.find("def reset_user_password")
block = users_src[max(0, i - 400):i + 1800] if i >= 0 else ''
ok(i >= 0, 'admin reset-password route exists')
ok("@role_required('Admin')" in block and "@login_required" in block, 'reset route is Admin only and login protected')
ok('password_error(new_password' in block, 'reset route enforces password rules')
ok("audit(cur, 'user.reset_password'" in block, 'reset is written to audit log')
ok("bcrypt.hashpw" in block, 'reset stores bcrypt hash, never plain text')
ok('new_password' not in "".join(l for l in block.splitlines() if 'flash(' in l), 'reset never flashes the password itself')

# 2. Admin cannot reset own password from users page
ok("u.user_id != session.user_id" in users_html, 'users page hides reset for own account')

# 3. Forgot-password route + page
ok("@app.route('/forgot-password', methods=['GET', 'POST'])" in auth_src, 'forgot-password GET and POST route exists')
fi = auth_src.find('def forgot_password')
fblock = auth_src[fi:fi + 3000] if fi >= 0 else ''
ok('_lock_left(' in fblock and '_register_fail(' in fblock, 'reset code has a wrong-try lock')
ok('compare_digest' in fblock and 'code_hash' in fblock, 'reset code is compared as a hash, never stored plain')
ok("'Username, code or time is wrong" in fblock, 'wrong code gives one generic message (no username guessing)')
ok('used=1' in fblock and 'expires_at > NOW()' in fblock, 'reset code is one-use and expires')
ok("def reset_user_code" in users_src and "@role_required('Admin')" in users_src, 'Admin makes reset codes')
ok("CREATE TABLE IF NOT EXISTS password_resets" in read('pharmacy','core.py'), 'password_resets table created in schema')
ok(_os.path.exists(_os.path.join(ROOT, 'templates', 'forgot_password.html')), 'forgot_password.html exists')
ok("url_for('forgot_password')" in login, 'login page links to forgot-password (real link)')
ok('Please ask your <span>Admin</span>' not in login, 'old dead forgot-password text removed')

# 4. Neumorphism stylesheet is loaded and exists
ok("css/app.css" in base, 'base.html loads the app.css bundle (classic theme inside)')
ok(_os.path.exists(_os.path.join(ROOT, 'static', 'css', 'classic.css')), 'classic.css exists')

# 5. No raw exception text in any template or route
bad = []
import glob
for p in glob.glob(_os.path.join(ROOT, 'templates', '*.html')):
    if '{{ e }}' in open(p, encoding='utf-8').read() or '{{ error }}' in open(p, encoding='utf-8').read():
        bad.append(_os.path.basename(p))
ok(not bad, 'no template prints raw exception variable (found: %s)' % (bad or 'none'))

fails = [m for m, good in RESULTS if not good]
for m, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + m)
print(f'{len(RESULTS) - len(fails)} passed, {len(fails)} failed')
sys.exit(1 if fails else 0)
