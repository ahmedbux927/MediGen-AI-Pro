"""Profit margin per item (v87.04): rules and wiring checks. No MySQL needed.
Run: python tests/test_margins.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import margins as MG

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

r = MG.compute(100, 80)
ok(r == {'margin': 20.0, 'pct': 20.0, 'status': 'ok'}, 'price 100, cost 80: margin 20 (20%), healthy')
ok(MG.compute(100, 95)['status'] == 'low', 'margin 5% is flagged low')
ok(MG.compute(100, 100)['status'] == 'low', 'zero margin is low, not loss')
ok(MG.compute(100, 120)['status'] == 'loss' and MG.compute(100, 120)['margin'] == -20.0, 'sold below cost is loss')
ok(MG.compute(0, 80)['status'] == 'no_price' and MG.compute(None, 80)['status'] == 'no_price', 'price 0 or missing: no sale price')
ok(MG.compute(100, 0)['status'] == 'no_cost' and MG.compute(100, None)['status'] == 'no_cost', 'cost 0 or missing: no cost')
ok(MG.compute(100, 90)['pct'] == 10.0 and MG.compute(100, 90)['status'] == 'ok', 'exactly 10% is healthy (boundary)')
ok(MG.compute('abc', 'x')['status'] == 'no_price', 'text values do not crash the rule')
ok(MG.pick_cost(55, 70) == (55.0, 'batch'), 'last batch cost is used first')
ok(MG.pick_cost(None, 70) == (70.0, 'item'), 'item cost is used when no batch cost')
ok(MG.pick_cost(0, 0) == (None, None), 'no cost anywhere gives none')

rows = [dict(MG.compute(100, 80), name='B'), dict(MG.compute(100, 120), name='A'),
        dict(MG.compute(0, 5), name='C'), dict(MG.compute(100, 95), name='D')]
for x in rows:
    x['pct'] = x['pct']
rows.sort(key=MG.sort_key)
ok([x['name'] for x in rows] == ['A', 'C', 'D', 'B'], 'worst first: loss, no price, low, healthy')
c = MG.counts(rows)
ok(c['loss'] == 1 and c['no_price'] == 1 and c['low'] == 1 and c['ok'] == 1 and c['no_cost'] == 0, 'counts per status')

src = read('pharmacy/routes/margins.py')
ok('from . import margins' in read('pharmacy/routes/__init__.py'), 'margin routes are registered')
ok("@role_required(*MARGIN_ROLES)" in src and "MARGIN_ROLES = ('Admin', 'Pharmacist')" in src, 'only Admin and Pharmacist')
ok(not re.search(r"(INSERT|UPDATE|DELETE)\s", src), 'margin report never writes')
ok('MAX(batch_id) AS last_id' in src, 'cost uses the last received batch')
ok('is_deleted = 0' in src, 'deleted items are left out')
ok(all('@guarded' in b and '@login_required' in b for b in re.split(r"\n(?=@app\.route)", src) if '@app.route' in b),
   'margin route is login-protected and guarded')
ok(os.path.exists(os.path.join(ROOT, 'templates/margins.html')), 'margins.html exists')
ok("url_for('margins')" in read('templates/base.html') or "'margins'," in read('pharmacy/routes/hubs.py'), 'Profit Margin is linked (sidebar or Finance hub)')
import py_compile
for f in ['pharmacy/routes/margins.py', 'pharmacy/services/margins.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
