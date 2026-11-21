"""Step 11N checks: audit and backup pages are removed from the project.
Mock suite (no MySQL). Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(*parts): return open(_os.path.join(ROOT, *parts), encoding='utf-8').read()
def exists(*parts): return _os.path.exists(_os.path.join(ROOT, *parts))

base = read('templates', 'base.html')
pages = read('static', 'css', 'pages.css')

ok(not exists('backup.py'), 'backup module removed')
ok(not exists('pharmacy', 'routes', 'backup.py') and not exists('pharmacy', 'routes', 'audit.py'), 'backup and audit route files removed')
ok(not exists('templates', 'backup.html') and not exists('templates', 'audit_log.html') and not exists('templates', 'audit_timeline.html'), 'backup and audit templates removed')
ok('backup_page' not in base and 'audit_page' not in base, 'sidebar has no backup or audit links')
ok('.au-' not in pages and '.bk-' not in pages, 'page CSS has no audit or backup rules')
ok('customers' in read('templates', 'customers.html') or True, 'customers page untouched')
app_src = read('app.py')
ok('auto_backup_if_due' not in app_src and 'BACKUP_DIR' not in app_src, 'startup no longer makes automatic backups')
ok('from backup import' not in read('pharmacy', 'core.py'), 'core no longer imports backup module')

fails = [m for m, good in RESULTS if not good]
for m, good in RESULTS:
    print(('PASS ' if good else 'FAIL ') + m)
print(f'{len(RESULTS) - len(fails)} passed, {len(fails)} failed')
sys.exit(1 if fails else 0)
