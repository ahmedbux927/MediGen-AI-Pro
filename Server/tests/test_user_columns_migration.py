"""Every column the profile page saves must be added automatically to older databases.
Otherwise a profile save fails with 'Unknown column' on any database made from an older schema."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import re, sys, unittest


def _read(*parts):
    with open(_os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return f.read()


class UserColumnsMigrationTest(unittest.TestCase):
    def setUp(self):
        self.core = _read('pharmacy', 'core.py')
        lib = _read('pharmacy', 'lib.py')
        m = re.search(r"PROFILE_FIELDS = \[(.*?)\]", lib, re.S)
        self.profile_fields = re.findall(r"'(\w+)'", m.group(1))

    def test_every_profile_field_has_a_migration(self):
        missing = [f for f in self.profile_fields if f != 'full_name' and ("('%s'," % f) not in self.core]
        self.assertEqual(missing, [], 'profile columns with no auto-add: %s' % missing)

    def test_access_and_picture_columns_have_a_migration(self):
        for col in ('is_active', 'access_start_time', 'access_end_time', 'profile_pic'):
            self.assertIn("('%s'," % col, self.core, col)

    def test_migration_runs_inside_schema_setup(self):
        self.assertIn("ALTER TABLE users ADD COLUMN {col} {ddl}", self.core)


if __name__ == '__main__':
    import unittest as _u
    suite = _u.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = _u.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
