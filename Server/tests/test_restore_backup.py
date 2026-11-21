"""Restore helper (backend track): file order, safety stops. No MySQL needed.
Run: python tests/test_restore_backup.py
"""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import restore_backup as R

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

folder = tempfile.mkdtemp()
for n in ['pharmacy_management_system_sales.sql', 'pharmacy_management_system_medicines.sql',
          'pharmacy_management_system_routines.sql', 'other_db_users.sql', 'readme.txt']:
    open(os.path.join(folder, n), 'w').close()
tables, views = R.plan_files(folder, 'pharmacy_management_system')
ok([n for n, _ in tables] == ['medicines', 'sales'], 'tables load in name order')
ok([n for n, _ in views] == ['routines'], 'the views file is separated and loaded last')
ok(all('other_db' not in p for _, p in tables + views), 'files of another database are ignored')

for bad, label in [('pharmacy_management_system', 'live database name is refused'),
                   ('bad name;drop', 'unsafe name is refused')]:
    try:
        R.check_target(bad, 'pharmacy_management_system'); ok(False, label)
    except SystemExit:
        ok(True, label)
try:
    R.check_target('pharmacy_restore_check', 'pharmacy_management_system'); ok(True, 'a new check name is accepted')
except SystemExit:
    ok(False, 'a new check name is accepted')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
