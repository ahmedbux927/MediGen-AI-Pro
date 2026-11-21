"""
Checks the least-privilege database user script and its guide (v27).
Run: python tests/test_db_user_setup.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

sql = open(os.path.join(ROOT, 'database/create_app_user.sql'), encoding='utf-8').read()
doc = open(os.path.join(ROOT, 'docs/DB_USER_SETUP.md'), encoding='utf-8').read()
code = '\n'.join(l for l in sql.splitlines() if not l.lstrip().startswith('--'))
ok('CREATE USER IF NOT EXISTS' in code, 'script creates a dedicated user')
ok('CHANGE_ME_STRONG_PASSWORD' in code and 'IDENTIFIED BY' in code, 'password is a placeholder, not a real secret')
ok('ALL PRIVILEGES' not in code.upper(), 'no ALL PRIVILEGES grant')
ok('ON `pharmacy_management_system`.*' in code, 'grants are limited to the app database')
ok('TO \'medigen_app\'@\'localhost\'' in code, 'grants go to the new user only')
for right in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRIGGER', 'EVENT', 'LOCK TABLES', 'SHOW VIEW']:
    ok(right in code, f'{right} is granted (needed by the app or the backup)')
ok('DB_USER=medigen_app' in doc and 'Rollback' in doc, 'guide shows the .env change and a rollback')
ok('pharmacy_management_system' in doc or 'create_app_user.sql' in doc, 'guide points to the script')

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
