"""Remember me: 30-day login on this PC, token stored as a hash only, cleared on logout and password change."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import re, sys, unittest


def _read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


class RememberMeTest(unittest.TestCase):
    def setUp(self):
        self.core = _read('pharmacy/core.py')
        self.auth = _read('pharmacy/routes/auth.py')

    def test_table_stores_hash_not_token(self):
        self.assertIn('CREATE TABLE IF NOT EXISTS remember_tokens', self.core)
        self.assertIn('token_hash CHAR(64)', self.core)
        self.assertIn('hashlib.sha256', self.core)
        self.assertNotRegex(self.core, r"INSERT INTO remember_tokens \(token\b")

    def test_cookie_is_httponly_lax_and_30_days(self):
        self.assertIn('REMEMBER_DAYS = 30', self.core)
        self.assertIn('httponly=True', self.core)
        self.assertIn("samesite='Lax'", self.core)
        self.assertIn('secure=Config.SESSION_COOKIE_SECURE', self.core)

    def test_login_sets_cookie_only_when_ticked(self):
        self.assertIn("request.form.get('remember')", self.auth)
        self.assertIn('set_remember_cookie(resp, remember_login(', self.auth)

    def test_restore_checks_active_user_and_access_window(self):
        m = re.search(r"def _restore_remembered_login\(\):(.*?)\n@app\.before_request", self.core, re.S)
        body = m.group(1) if m else ''
        self.assertIn('u.is_active = TRUE', body)
        self.assertIn('t.expires_at > NOW()', body)
        self.assertIn('_within_access_window', body)

    def test_remember_me_writes_diagnostic_log_lines(self):
        self.assertIn("remember-me: cookie set for user", self.auth)
        self.assertIn("remember-me: cookie present but no active token", self.core)
        self.assertIn("remember-me: logged user", self.core)

    def test_restore_runs_before_session_sync(self):
        self.assertLess(self.core.index('def _restore_remembered_login'), self.core.index('def _sync_session_user'))

    def test_logout_removes_token_and_cookie(self):
        m = re.search(r"def logout\(\):(.*?)\n\n", self.auth, re.S)
        body = m.group(1) if m else ''
        self.assertIn('forget_login(', body)
        self.assertIn('clear_remember_cookie(', body)

    def test_password_changes_end_remembered_logins(self):
        for rel in ('pharmacy/routes/auth.py', 'pharmacy/routes/users.py', 'pharmacy/routes/profile.py'):
            self.assertIn('DELETE FROM remember_tokens', _read(rel), rel)

    def test_login_page_has_checkbox(self):
        self.assertIn('name="remember"', _read('templates/login.html'))


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
