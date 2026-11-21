"""Seasonal purchase forecast (v87.12): rules and wiring. No MySQL needed.
Run: python tests/test_purchase_forecast.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import purchase_forecast as PF

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

f = PF.forecast(recent=10, last_year=10, stock=0, reorder=0)
ok(f['expected'] == 10 and f['suggested'] == 10 and not f['seasonal'], 'steady sales: next 30 days = recent sales, order the gap')
f = PF.forecast(recent=10, last_year=60, stock=5, reorder=0)
ok(f['seasonal'] is True and f['expected'] == 60 and f['suggested'] == 55, 'season: last year 60 vs recent 10 is seasonal, uses the higher rate')
ok('same 30 days last year' in f['reason'], 'seasonal reason names last year')
f = PF.forecast(recent=0, last_year=3, stock=0, reorder=0)
ok(f['seasonal'] is False, 'a tiny last year (under 5 units) is not called a season')
f = PF.forecast(recent=0, last_year=0, stock=0, reorder=0)
ok(f['suggested'] == 0 and f['expected'] == 0, 'no sales at all: no suggestion')
f = PF.forecast(recent=2, last_year=0, stock=50, reorder=0)
ok(f['suggested'] == 0, 'enough stock: no suggestion')
f = PF.forecast(recent=1, last_year=0, stock=2, reorder=20)
ok(f['suggested'] == 18, 'reorder level sets the minimum target')
f = PF.forecast(recent=None, last_year=None, stock=None, reorder=None)
ok(f['suggested'] == 0, 'missing numbers are treated as zero')
f = PF.forecast(recent=-5, last_year=10, stock=0, reorder=0)
ok(f['expected'] == 10, 'a negative net sale (more returns) is treated as zero')

src = read('pharmacy/routes/purchase_forecast.py')
ok("FORECAST_ROLES = ('Admin', 'Pharmacist')" in src and "@role_required(*FORECAST_ROLES)" in src, 'only Admin and Pharmacist')
ok(not re.search(r"\b(INSERT|UPDATE|DELETE)\b", src), 'the forecast never writes (no order, no stock change)')
ok('INTERVAL 365 DAY' in src and 'INTERVAL 335 DAY' in src, 'last year window is the same 30 days, one year back')
ok('sale_return_items' in src, 'sales are net of returns, same as the purchase suggestions')
ok('all three' not in src and all('@guarded' in b and '@login_required' in b for b in re.split(r"\n(?=@app\.route)", src) if '@app.route' in b),
   'the forecast route is login-protected and guarded')
ok('nothing is ordered here' in read('templates/purchase_forecast.html').lower(), 'the page says nothing is ordered here')
ok("'purchase_forecast'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'Purchase Forecast link is in the sidebar')

import py_compile
for f_ in ['pharmacy/services/purchase_forecast.py', 'pharmacy/routes/purchase_forecast.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f_), doraise=True); ok(True, f_ + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f_ + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
