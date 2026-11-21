"""Stock count screen (v87.00): static checks on routes, roles, templates and navigation. No MySQL needed.
Run: python tests/test_stock_count_routes.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

route_src = read('pharmacy/routes/stock_count.py')
init_src = read('pharmacy/routes/__init__.py')
base_src = read('templates/base.html')

ok('from . import stock_count' in init_src, 'stock_count routes are registered in routes/__init__.py')

routes = re.findall(r"@app\.route\('([^']+)'(?:, methods=\['POST'\])?\)", route_src)
expected = ['/stock-count', '/stock-count/start', '/stock-count/<int:count_id>', '/stock-count/<int:count_id>/save',
            '/stock-count/<int:count_id>/submit', '/stock-count/<int:count_id>/reopen',
            '/stock-count/<int:count_id>/cancel', '/stock-count/<int:count_id>/approve']
ok(sorted(routes) == sorted(expected), 'all eight stock count URLs exist')

# every state-changing route is POST only
posts = re.findall(r"@app\.route\('([^']+)', methods=\['POST'\]\)", route_src)
ok(len(posts) == 6 and all(p.startswith('/stock-count/') for p in posts), 'six POST-only actions (start, save, submit, reopen, cancel, approve)')

# approve is Admin only, and nothing else is
blocks = re.split(r"\n(?=@app\.route)", route_src)
approve = [b for b in blocks if "def stock_count_approve" in b]
ok(len(approve) == 1 and "@role_required('Admin')" in approve[0], 'approve route is restricted to Admin')
others = [b for b in blocks if "@app.route" in b and "def stock_count_approve" not in b]
ok(all("@role_required(*COUNT_ROLES)" in b for b in others), 'every other stock count route allows Admin and Pharmacist only')
ok(all('@guarded' in b and '@login_required' in b for b in blocks if '@app.route' in b),
   'every stock count route is login-protected and guarded')

ok('@role_required' in route_src and 'Cashier' not in route_src.split('COUNT_ROLES')[1].split('\n')[0],
   'Cashier is not in the stock count roles')

ok("SC.approve_count(cur, count_id, session['user_id'], session.get('role'), audit)" in route_src,
   'approval passes the logged-in user and role to the service')
ok("request.form.getlist('medicine_id')" in route_src and "request.form.getlist('counted_qty')" in route_src,
   'save reads medicine ids and counted quantities as paired lists')
ok('MAX_SAVE_LINES' in route_src, 'save is capped in size')

for t in ('templates/stock_count.html', 'templates/stock_count_detail.html'):
    ok(os.path.exists(os.path.join(ROOT, t)), f'{t} exists')
detail = read('templates/stock_count_detail.html')
ok('name="counted_qty"' in detail and 'inputmode="numeric"' in detail, 'count sheet has a numeric box per medicine')
ok("{% if clash %}disabled{% endif %}" in detail, 'approve button is disabled while stock conflicts exist')
ok('Save counts' in detail and 'Submit for approval' in detail and 'Approve and update stock' in detail,
   'detail page has save, submit and approve actions')

ok("'stock_count_home'" in base_src + read('pharmacy/routes/hubs.py'), 'Stock Count link is in the sidebar')

ok(os.path.exists(os.path.join(ROOT, 'database/migrations/003_stock_counts.sql')), 'count tables migration exists')

import py_compile
try:
    py_compile.compile(os.path.join(ROOT, 'pharmacy/routes/stock_count.py'), doraise=True)
    py_compile.compile(os.path.join(ROOT, 'pharmacy/services/stock_count.py'), doraise=True)
    ok(True, 'routes and service compile')
except py_compile.PyCompileError as e:
    ok(False, 'routes and service compile: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
