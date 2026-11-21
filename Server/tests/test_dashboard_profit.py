"""Static checks for the dashboard profit and loss card (v86.59). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/dashboard.py')
tpl = read('templates/dashboard.html')
ok("from pharmacy.routes.reports import _section_rows as _pl_rows" in route, 'dashboard reuses the reports section profit function (one formula)')
ok('pl_totals = ' in route and 'pl_rows=pl_rows' in route, 'route passes the per-section rows and totals to the template')
ok('profit and loss by section failed (dashboard still opens)' in route, 'a failure here never breaks the dashboard')
ok("rec.sections" in tpl and 'Profit and loss, this month' in tpl and 'Loss' in tpl and 'T.profit_month' in tpl, 'template shows month profit or loss per section with totals')
ok("dv-neg" in tpl and "s['profit_month'] >= 0" in tpl, 'loss is shown in red')
ok('for k, lab, ic, _d in PS.SECTIONS' in route, 'every product section is listed (medicines, syrups, creams, drip, other)')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
