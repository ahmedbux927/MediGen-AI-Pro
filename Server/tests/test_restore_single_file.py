"""v82: restore one mysqldump .sql file (from backups\\ made by scripts/backup_db.py) into a NEW check database.
Run: python tests/test_restore_single_file.py   (also run by tests/run_all.py)"""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, _os.path.join(ROOT, 'scripts')); sys.path.insert(0, ROOT)
import restore_backup as R
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

ok(R.plan_single('backups/medigen_20261025_1200.sql') == [('whole backup', 'backups/medigen_20261025_1200.sql')],
   'a single backup file is loaded as one piece (tables, data, triggers in mysqldump order)')
try:
    R.plan_single('backups/notes.txt'); refused = False
except SystemExit as e:
    refused = '.sql' in str(e)
ok(refused, 'a non-.sql file is refused')
src = open(_os.path.join(ROOT, 'scripts', 'restore_backup.py'), encoding='utf-8').read()
ok("os.path.isfile(args.folder)" in src, 'the script tells a single file from a folder')
ok("'SHOW TABLES'" in src, 'row counts for a single file come from the tables in the new database')
ok("if not args.prefix:" in src, 'a folder still needs --prefix, as before')
ok("check_target(args.db, live)" in src and "already exists. Drop it first" in src, 'the live database and existing names are still refused')
ok('--routines' in open(_os.path.join(ROOT, 'scripts', 'backup_db.py'), encoding='utf-8').read() and '--triggers' in open(_os.path.join(ROOT, 'scripts', 'backup_db.py'), encoding='utf-8').read(),
   'the daily backup includes triggers and routines')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
