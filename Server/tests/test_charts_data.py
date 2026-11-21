"""
Chart data checks: every day in the range gets a point, days without sales are zero,
and the dashboard/reports pages are never served from a stale cache.
Run: python tests/test_charts_data.py
"""
import os, sys
import types
from datetime import date
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

# Same stub the other mock tests use: no MySQL server is needed for these checks.
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = None
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m
if 'bcrypt' not in sys.modules:
    try:
        import bcrypt  # noqa: F401
    except ImportError:
        b = types.ModuleType('bcrypt')
        b.gensalt = lambda *a, **k: b'salt'
        b.hashpw = lambda pw, salt: b'h:' + pw
        b.checkpw = lambda pw, hashed: hashed == b'h:' + pw
        sys.modules['bcrypt'] = b
from pharmacy.lib import _fill_days

# Gap days are filled with zero, oldest first, start and end included.
rows = [{'day': date(2026, 10, 14), 'invoices': 2, 'revenue': 500.5},
        {'day': date(2026, 10, 18), 'invoices': 1, 'revenue': 120}]
out = _fill_days(rows, date(2026, 10, 12), date(2026, 10, 18), 'day')
ok(len(out) == 7, 'a 7-day window gives 7 points, not only the days with sales')
ok([r['day'].day for r in out] == [12, 13, 14, 15, 16, 17, 18], 'days run oldest to newest with no gaps')
ok(out[0]['revenue'] == 0 and out[0]['invoices'] == 0, 'a day without sales is zero')
ok(out[2]['revenue'] == 500.5 and out[2]['invoices'] == 2, 'a day with sales keeps its totals')
ok(out[6]['revenue'] == 120 and out[6]['invoices'] == 1, 'today is included')

# Text dates (as they come from settings or the URL) are accepted too.
out2 = _fill_days([], '2026-10-01', '2026-10-03', 'sale_day')
ok([r['sale_day'] for r in out2] == [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)],
   'text start/end dates work and the key name is kept')
ok(all(r['revenue'] == 0.0 for r in out2), 'empty input gives zero for every day')

# Same day for start and end gives one point.
ok(len(_fill_days([], date(2026, 10, 5), date(2026, 10, 5), 'd')) == 1, 'single-day range gives one point')

dash = open(os.path.join(ROOT, 'pharmacy/routes/dashboard.py'), encoding='utf-8').read()
rep = open(os.path.join(ROOT, 'pharmacy/routes/reports.py'), encoding='utf-8').read()
ok('BETWEEN %s AND %s' in dash and 'INTERVAL 7 DAY' not in dash, 'dashboard uses an exact 7-day window')
ok("'Cache-Control'] = 'no-store'" in dash and "'Cache-Control'] = 'no-store'" in rep,
   'dashboard and reports send no-store')
ok('HAVING sold > 0' in dash and 'sale_return_items' in dash, 'top sellers are net of returns (same as reports)')
tpl = open(os.path.join(ROOT, 'templates/dashboard.html'), encoding='utf-8').read()
ok('{% if chart_has_data %}' in tpl, 'sales chart shows the empty message only when there is no sale')

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
