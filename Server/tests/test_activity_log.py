"""Static checks for the Activity Log page (v86.49). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/activity_log.py')
repo = read('pharmacy/repos/activity_log.py')
tpl = read('templates/activity_log.html')
ok("@app.route('/activity-log')" in route and "role_required('Admin')" in route, 'activity log page exists, Admin only')
ok('@guarded' in route, 'activity log route is guarded')
ok('INSERT ' not in repo and 'UPDATE ' not in repo and 'DELETE ' not in repo, 'activity log repo only reads')
ok('%s' in repo and 'f"' not in repo and ".format(" not in repo, 'filters use parameters, not string formatting')
ok('_like' in repo and "replace('%', '\\\\%')" in repo, 'user search escapes LIKE wildcards')
ok("_valid_date(request.args.get('from'" in route.replace(" ", "") or "_valid_date(request.args.get('from', ''))" in route, 'date filters are validated')
ok("from . import activity_log" in read('pharmacy/routes/__init__.py'), 'route registered')
ok("'activity_log'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'sidebar link added')
ok('{% extends' in tpl and 'name="user"' in tpl, 'template extends base and has the user filter')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
