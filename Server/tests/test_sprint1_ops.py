"""Sprint 1 checks: backup script, alerts page, supplier returns (source and template checks, no MySQL).
Run through tests/run_all.py."""
import os as _os, re, sys, tempfile, time, importlib.util
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

spec = importlib.util.spec_from_file_location('backup_db', _os.path.join(ROOT, 'scripts', 'backup_db.py'))
bk = importlib.util.module_from_spec(spec); spec.loader.exec_module(bk)

# ---- backup script ----
s = bk.load_settings({'DB_HOST': 'db.local', 'DB_USER': 'pharm', 'DB_PASSWORD': 'secret-pw', 'DB_NAME': 'pms'})
cmd = bk.build_command(s)
ok('--single-transaction' in cmd and '--routines' in cmd and '--triggers' in cmd, 'backup uses a consistent dump with routines and triggers')
ok(not any('secret-pw' in part for part in cmd), 'password is not on the mysqldump command line')
ok(cmd[cmd.index('-h') + 1] == 'db.local' and cmd[cmd.index('-u') + 1] == 'pharm' and cmd[-1] == 'pms', 'host, user and database name are passed')
ok(bk.load_settings({'DB_PASSWORD': 'from-env'}).get('password') == 'from-env', 'environment variables win over .env')
ok(bk.read_env_file(_os.path.join(ROOT, 'no-such-file.env')) == {}, 'a missing .env gives no settings, no crash')
ok(bk.backup_file_name(__import__('datetime').datetime(2026, 10, 17, 2, 30)) == 'medigen_20261017_0230.sql', 'backup file name has date and time')

tmp = tempfile.mkdtemp(prefix='mg_bk_')
for i in range(6):
    p = _os.path.join(tmp, f'medigen_2026101{i}_0230.sql')
    open(p, 'w').write('x' * 300)
    t = time.time() - (6 - i) * 60
    _os.utime(p, (t, t))
removed = bk.prune_old_backups(tmp, keep=3)
left = sorted(_os.listdir(tmp))
ok(len(removed) == 3 and len(left) == 3, 'only the newest 3 backups are kept')
ok(left == ['medigen_20261013_0230.sql', 'medigen_20261014_0230.sql', 'medigen_20261015_0230.sql'], 'the newest files are the ones kept')

bad = dict(s, mysqldump=_os.path.join(tmp, 'no-such-mysqldump'), backup_dir=tmp)
failed = False
try:
    bk.run_backup(bad)
except Exception:
    failed = True
ok(failed, 'a missing mysqldump is reported as a failure, not a silent success')
ok(not any(f.startswith('medigen_2026') and f.endswith('.sql') and _os.path.getsize(_os.path.join(tmp, f)) == 0 for f in _os.listdir(tmp)), 'no empty backup file is left behind')

# ---- alerts and supplier returns: wiring (routes, templates, navigation) ----
routes_src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'supplier_returns.py'), encoding='utf-8').read()
ok("@app.route('/alerts')" in routes_src and "@app.route('/supplier-returns')" in routes_src, 'alerts and supplier returns routes exist')
ok("@app.route('/supplier-returns/new', methods=['POST'])" in routes_src, 'supplier return save is POST only')
ok(routes_src.count('@role_required(') >= 3 and "role_required('Cashier')" not in routes_src, 'alerts and returns are for Admin and Pharmacist only')
ok('FOR UPDATE' in routes_src and 'rollback()' in routes_src, 'supplier return locks the batch and rolls back on error')
ok("'Supplier return'" in routes_src and 'INSERT INTO supplier_returns' in routes_src, 'return writes stock history and the return record')
ok('qty > b[\'quantity\']' in routes_src, 'return cannot be more than the units in the batch')
ok(_os.path.exists(_os.path.join(ROOT, 'templates', 'alerts.html')) and _os.path.exists(_os.path.join(ROOT, 'templates', 'supplier_returns.html')), 'both templates exist')
base = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
_hubs_src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'hubs.py'), encoding='utf-8').read()
ok("'alerts'" in base + _hubs_src and "'supplier_returns'" in base + _hubs_src, 'both pages are reachable from a hub')
core = open(_os.path.join(ROOT, 'pharmacy', 'core.py'), encoding='utf-8').read()
ok('CREATE TABLE IF NOT EXISTS supplier_returns' in core, 'supplier_returns table is created on start')
ok('from . import supplier_returns' in open(_os.path.join(ROOT, 'pharmacy', 'routes', '__init__.py'), encoding='utf-8').read(), 'routes are registered')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
