"""Cold chain log (v87.01): rules, saving, and route/nav checks. No MySQL needed.
Run: python tests/test_cold_chain.py
"""
import os, re, sys
from decimal import Decimal
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import temperature as TP

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

def raises(fn, part, label):
    try:
        fn(); ok(False, label)
    except TP.TemperatureError as e:
        ok(part in str(e), label)

ok(TP.parse_reading('5.2') == Decimal('5.2'), 'parses 5.2')
ok(TP.parse_reading('5,2') == Decimal('5.2'), 'accepts a comma as decimal point')
ok(TP.parse_reading(' 8 ') == Decimal('8.0'), 'accepts spaces and whole numbers')
raises(lambda: TP.parse_reading('abc'), 'must be a number', 'text is refused with a clear message')
raises(lambda: TP.parse_reading('99'), 'looks wrong', 'impossible high value is refused')
raises(lambda: TP.parse_reading('-41'), 'looks wrong', 'impossible low value is refused')
ok(TP.is_in_range(Decimal('2.0')) and TP.is_in_range(Decimal('8.0')), 'limits 2.0 and 8.0 are in range')
ok(not TP.is_in_range(Decimal('1.9')) and not TP.is_in_range(Decimal('8.1')), 'just outside the limits is out of range')

class Cur:
    def __init__(self):
        self.log, self.lastrowid = [], 11
    def execute(self, sql, p=None):
        self.log.append((' '.join(sql.split()), p))

c = Cur()
r = TP.record_reading(c, '  Fridge 1 ', '5.5', 3, 'checked')
ok(r['in_range'] is True and r['log_id'] == 11, 'in-range reading is saved as in range')
ok(c.log[0][1] == ('Fridge 1', Decimal('5.5'), 1, 3, 'checked'), 'location is trimmed and values are stored')
c = Cur()
r = TP.record_reading(c, 'Fridge 1', '9.0', 3, '')
ok(r['in_range'] is False and c.log[0][1][2] == 0, 'out-of-range reading is still saved, flagged 0')
ok(c.log[0][1][4] is None or c.log[0][1][4] == '', 'empty note is stored as no note')
raises(lambda: TP.record_reading(Cur(), '   ', '5', 3), 'name the place', 'a reading without a place is refused')
raises(lambda: TP.record_reading(Cur(), 'Fridge 1', 'x', 3), 'must be a number', 'a bad number is refused before saving')

route_src = read('pharmacy/routes/cold_chain.py')
init_src = read('pharmacy/routes/__init__.py')
base_src = read('templates/base.html')
ok('from . import cold_chain' in init_src, 'cold chain routes are registered')
urls = re.findall(r"@app\.route\('([^']+)'", route_src)
ok(sorted(urls) == ['/cold-chain', '/cold-chain/record'], 'two URLs: the log page and the save action')
ok("methods=['POST']" in route_src and route_src.count("@role_required(*COLD_ROLES)") == 2, 'save is POST only; both routes use the cold chain roles')
ok("COLD_ROLES = ('Admin', 'Pharmacist', 'Cashier')" in route_src, 'all three shop roles can record readings')
ok('delete' not in route_src.lower(), 'no delete route: readings cannot be removed')
ok(all('@guarded' in b and '@login_required' in b for b in re.split(r"\n(?=@app\.route)", route_src) if '@app.route' in b),
   'every cold chain route is login-protected and guarded')
ok("TP.record_reading(cur, location, temperature, session['user_id'], note)" in route_src, 'save goes through the service rules')
ok(os.path.exists(os.path.join(ROOT, 'templates/cold_chain.html')), 'cold_chain.html exists')
tpl = read('templates/cold_chain.html')
ok('name="temperature"' in tpl and 'name="location"' in tpl and 'inputmode="decimal"' in tpl, 'form has place, temperature and note fields')
ok("'cold_chain'" in base_src + read('pharmacy/routes/hubs.py'), 'Cold Chain Log link is in the sidebar')
ok(os.path.exists(os.path.join(ROOT, 'database/migrations/006_temperature_logs.sql')), 'temperature_logs migration exists')

import py_compile
try:
    py_compile.compile(os.path.join(ROOT, 'pharmacy/routes/cold_chain.py'), doraise=True)
    ok(True, 'cold chain route compiles')
except py_compile.PyCompileError as e:
    ok(False, 'cold chain route compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
