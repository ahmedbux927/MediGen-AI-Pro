"""Checks for the cash drawer (v86.60). Run through tests/run_all.py or directly.
The maths is tested directly. The routes and template are checked by reading the code."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

_sys.path.insert(0, ROOT)
from pharmacy.services import cash_drawer as CD   # pure functions, no database needed

ok(CD.expected_cash(5000, 3000, 200, 0, 0) == 7800, 'expected = opening + cash sales - refunds')
ok(CD.expected_cash(5000, 3000, 0, 500, 200) == 8300, 'expected includes cash in and cash out')
ok(CD.shortage(7600, 7800) == -200, 'counted less than expected is a shortage (negative)')
ok(CD.shortage(8000, 7800) == 200, 'counted more than expected is extra (positive)')
ok(CD.shortage(7800, 7800) == 0, 'exact count gives zero')
ok(CD.describe(-200)[0] == 'short' and 'short by' in CD.describe(-200)[1], 'short result is labelled')
ok(CD.describe(200)[0] == 'extra', 'extra result is labelled')
ok(CD.describe(0)[0] == 'ok', 'zero difference is labelled ok')
ok(CD.expected_cash('0.1', '0.2', 0, 0, 0) == 0.3, 'string amounts from forms are handled')

route = read('pharmacy/routes/cash_drawer.py')
repo = read('pharmacy/repos/cash_drawer.py')
tpl = read('templates/cash_drawer.html')
ok("@role_required(*ROLES)" in route and "ROLES = ('Admin', 'Pharmacist', 'Cashier')" in route, 'drawer open to Admin, Pharmacist and Cashier')
ok(route.count('@guarded') == 4, 'every drawer route is guarded')
ok("'cash.close'" in route and "'cash.open'" in route and "'cash.in' if kind" in route, 'open, cash in/out and close are audited')
ok('shortage' in route and 'CD.describe(diff)' in route, 'closing shows the shortage or extra')
ok('UPDATE cash_sessions' in repo and 'closed_at IS NULL' in repo, 'a closed session cannot be closed again')
ok('DELETE' not in repo, 'no delete in the drawer code')
ok('FROM sale_payments' in repo and "method = 'Cash'" in repo and 'created_at >= %s' in repo, 'cash received (sales and udhaar repaid) counted from sale_payments only once')
ok("kind ENUM" not in tpl and "name=\"kind\"" in tpl, 'form sends in or out only')
ok('{% extends' in tpl and 'csrf_token' in tpl, 'template extends base and forms carry csrf token')
ok("url_for('cash_drawer')" in read('templates/base.html') or "'cash_drawer'," in read('pharmacy/routes/hubs.py'), 'cash drawer is linked (sidebar or Finance hub)')
ok('CREATE TABLE IF NOT EXISTS cash_sessions' in read('pharmacy/core.py') and 'CREATE TABLE IF NOT EXISTS cash_movements' in read('pharmacy/core.py'), 'tables created at startup')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
