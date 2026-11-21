"""Bundled MySQL launcher: does nothing without the mysql folder, binds to this PC only, passwords never on the command line."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, unittest

sys.path.insert(0, ROOT)


class BundledMysqlTest(unittest.TestCase):
    def setUp(self):
        import bundled_mysql
        self.m = bundled_mysql

    def test_no_op_without_mysql_folder(self):
        if _os.path.isfile(self.m._tool('mysqld')):
            self.skipTest('a bundled mysql folder is present here')
        self.assertFalse(self.m.available())
        self.assertIsNone(self.m.start())

    def test_server_binds_to_this_pc_only(self):
        args = self.m._server_args()
        self.assertIn('--bind-address=127.0.0.1', args)
        self.assertFalse(any('0.0.0.0' in a for a in args))

    def test_binary_log_is_off_so_audit_triggers_can_be_created(self):
        self.assertIn('--skip-log-bin', self.m._server_args())

    def test_first_admin_is_offered_when_database_is_empty(self):
        with open(_os.path.join(ROOT, 'desktop.py'), encoding='utf-8') as f:
            src = f.read()
        self.assertIn('def _create_first_admin', src)
        self.assertIn("_admin_count() == 0", src)

    def test_uses_its_own_port(self):
        self.assertEqual(self.m.PORT, 3307)
        self.assertIn('--port=3307', self.m._server_args())

    def test_password_is_passed_by_environment_not_command_line(self):
        import inspect
        src = inspect.getsource(self.m._client)
        self.assertIn("env['MYSQL_PWD']", src)
        self.assertNotIn("'-p", src)

    def test_passwords_are_random_and_sql_safe(self):
        import secrets, re
        for _ in range(20):
            self.assertRegex(secrets.token_urlsafe(18), r'^[A-Za-z0-9_-]+$')

    def test_config_reads_db_port(self):
        with open(_os.path.join(ROOT, 'config.py'), encoding='utf-8') as f:
            self.assertIn("MYSQL_PORT = int(os.environ.get('DB_PORT', '3306'))", f.read())


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
