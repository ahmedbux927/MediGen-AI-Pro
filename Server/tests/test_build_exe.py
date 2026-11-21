"""The Windows build script must copy everything the program reads next to the exe."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, unittest


class BuildExeTest(unittest.TestCase):
    def setUp(self):
        with open(_os.path.join(ROOT, 'build_exe.bat'), encoding='utf-8') as f:
            self.bat = f.read()

    def test_builds_the_named_program(self):
        self.assertIn('--name MediGenAIPro', self.bat)
        self.assertIn('desktop.py', self.bat)

    def test_copies_templates_and_static_next_to_exe(self):
        self.assertIn('"templates" "dist\\MediGenAIPro\\templates"', self.bat)
        self.assertIn('"static" "dist\\MediGenAIPro\\static"', self.bat)

    def test_creates_backup_and_profile_folders(self):
        self.assertIn('dist\\MediGenAIPro\\backups', self.bat)
        self.assertIn('dist\\MediGenAIPro\\static\\profiles', self.bat)

    def test_refuses_to_build_without_offline_assets(self):
        self.assertIn('if not exist "static\\vendor"', self.bat)

    def test_config_reads_env_next_to_exe_when_frozen(self):
        with open(_os.path.join(ROOT, 'config.py'), encoding='utf-8') as f:
            cfg = f.read()
        self.assertIn("getattr(sys, 'frozen', False)", cfg)
        self.assertIn("sys.executable", cfg)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
