"""Name and role shown on every page come from the database on each request (so a rename shows at once)."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import re, sys, unittest


class SessionSyncTest(unittest.TestCase):
    def setUp(self):
        with open(_os.path.join(ROOT, 'pharmacy', 'core.py'), encoding='utf-8') as f:
            self.core = f.read()
        m = re.search(r"def _sync_session_user\(\):(.*?)\n@app\.before_request", self.core, re.S)
        self.body = m.group(1) if m else ''

    def test_sync_is_registered_as_before_request(self):
        self.assertIn('@app.before_request\ndef _sync_session_user', self.core)

    def test_name_and_role_are_refreshed(self):
        self.assertIn("session['user_name'] = row['full_name']", self.body)
        self.assertIn("session['role'] = row['role_name']", self.body)

    def test_deactivated_user_is_logged_out(self):
        self.assertIn("session.clear()", self.body)
        self.assertIn("row['is_active']", self.body)

    def test_login_and_logout_are_skipped(self):
        self.assertIn("'login', 'logout'", self.body)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
