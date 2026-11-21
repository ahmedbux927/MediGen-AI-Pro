"""The guarded() safety net: unexpected errors become friendly responses, HTTP errors pass through,
and POST failures never redirect to another website."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, unittest
sys.path.insert(0, ROOT); os_cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b''
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
class _Cur:
    def execute(self, *a, **k): pass
    def fetchone(self): return None
    def fetchall(self): return []
    def close(self): pass
class _Conn:
    def cursor(self): return _Cur()
    def commit(self): pass
    def rollback(self): pass
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = _Conn()
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m
import app as A
from pharmacy.lib import guarded
from werkzeug.exceptions import NotFound
_os.chdir(os_cwd)


def _boom():
    raise ValueError('database exploded')


class GuardedTest(unittest.TestCase):
    def test_unexpected_error_returns_500_not_crash(self):
        with A.app.test_request_context('/x', method='GET'):
            result = guarded(_boom)()
        body, code = result if isinstance(result, tuple) else (result, 200)
        self.assertEqual(code, 500)

    def test_post_failure_redirects_with_flash_message(self):
        with A.app.test_request_context('/x', method='POST'):
            resp = guarded(_boom)()
        self.assertEqual(resp.status_code, 302)

    def test_post_never_redirects_to_other_site(self):
        with A.app.test_request_context('/x', method='POST', headers={'Referer': 'https://evil.example/phish'}):
            resp = guarded(_boom)()
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('evil.example', resp.headers['Location'])

    def test_http_errors_pass_through(self):
        def not_here():
            raise NotFound()
        with A.app.test_request_context('/x', method='GET'):
            with self.assertRaises(NotFound):
                guarded(not_here)()

    def test_api_error_is_json(self):
        with A.app.test_request_context('/api/v1/medicines', method='GET'):
            result = guarded(_boom)()
        body, code = result
        self.assertEqual(code, 500)
        self.assertIn('error', body.get_json())


if __name__ == '__main__':
    # print one PASS line per passing test so tests/run_all.py counts them
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
