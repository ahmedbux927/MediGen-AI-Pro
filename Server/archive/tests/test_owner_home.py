"""Static checks for the Owner Summary (v86.49). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/owner_home.py')
tpl = read('templates/owner_home.html')
ok("@app.route('/owner')" in route and "role_required('Admin')" in route, 'owner page exists, Admin only')
ok('@guarded' in route, 'owner route is guarded')
ok('INSERT ' not in route and 'UPDATE ' not in route and 'DELETE ' not in route, 'owner page is read only')
ok("from . import owner_home" in read('pharmacy/routes/__init__.py'), 'route registered')
ok("url_for('owner_home')" in read('templates/base.html') or "'owner_home'," in read('pharmacy/routes/hubs.py'), 'owner summary is linked (sidebar or Finance hub)')
ok('{% extends' in tpl and 'os-slide' in tpl and 'max-width: 640px' in tpl, 'template extends base and is phone friendly (slides, one per screen on phones)')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
