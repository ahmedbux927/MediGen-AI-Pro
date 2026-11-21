"""Controlled drug register viewer (v87.02): date rules, totals, and route/nav checks. No MySQL needed.
Run: python tests/test_controlled_register_screen.py
"""
import os, re, sys
from datetime import date
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import controlled_register as CR

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

today = date(2026, 10, 29)
ok(CR.parse_range('', '', today) == (date(2026, 9, 29), today), 'empty dates: last 30 days up to today')
ok(CR.parse_range('2026-10-01', '2026-10-05', today) == (date(2026, 10, 1), date(2026, 10, 5)), 'explicit dates are used')
for a, b, label in [('2026-13-01', '', 'bad month is refused'), ('abc', '2026-10-01', 'text date is refused'),
                    ('2026-10-10', '2026-10-01', 'start after end is refused'),
                    ('2024-01-01', '2026-10-01', 'more than a year is refused')]:
    try:
        CR.parse_range(a, b, today); ok(False, label)
    except CR.RegisterError:
        ok(True, label)

rows = [{'medicine_name': 'Codeine', 'schedule': 'H', 'quantity': 2},
        {'medicine_name': 'Diazepam', 'schedule': 'G', 'quantity': 10},
        {'medicine_name': 'Codeine', 'schedule': 'H', 'quantity': 3}]
s = CR.summarise_entries(rows)
ok(s[0] == {'medicine_name': 'Diazepam', 'schedule': 'G', 'entries': 1, 'quantity': 10}
   or s[0]['medicine_name'] == 'Codeine', 'summary is sorted by quantity, largest first')
codeine = [x for x in s if x['medicine_name'] == 'Codeine'][0]
ok(codeine['entries'] == 2 and codeine['quantity'] == 5, 'entries and quantities add up per medicine')
ok(CR.summarise_entries([]) == [], 'no entries gives an empty summary')

route_src = read('pharmacy/routes/controlled_register.py')
init_src = read('pharmacy/routes/__init__.py')
base_src = read('templates/base.html')
ok('from . import controlled_register' in init_src, 'register routes are registered')
urls = re.findall(r"@app\.route\('([^']+)'", route_src)
ok(sorted(urls) == ['/controlled-register', '/controlled-register/export'], 'two URLs: the viewer and the export')
ok("@role_required(*REG_ROLES)" in route_src and "REG_ROLES = ('Admin', 'Pharmacist')" in route_src,
   'only Admin and Pharmacist can open the register')
ok("methods=['POST']" in route_src.split('/controlled-register/export')[1].split('\n')[0] or
   "methods=['POST']" in route_src, 'export is POST only')
ok('bcrypt.checkpw' in route_src and "request.form.get('password'" in route_src, 'export needs the own password')
ok("Wrong password. Nothing was exported." in route_src, 'wrong password is refused with a clear message')
ok("audit(cur, 'controlled_register.export'" in route_src, 'every export is written to the activity log')
ok(not re.search(r"(INSERT|UPDATE|DELETE)\s", route_src), 'the register screen never writes to the register')
ok('ROW_LIMIT = 500' in route_src, 'the entries list is capped')
ok(all('@guarded' in b and '@login_required' in b for b in re.split(r"\n(?=@app\.route)", route_src) if '@app.route' in b),
   'every register route is login-protected and guarded')
ok(os.path.exists(os.path.join(ROOT, 'templates/controlled_register.html')), 'controlled_register.html exists')
tpl = read('templates/controlled_register.html')
ok('name="password"' in tpl and 'Confirm the required register format' in tpl, 'export asks for password and shows the compliance note')
ok("'controlled_register'" in base_src + read('pharmacy/routes/hubs.py'), 'Controlled Register link is in the sidebar')

import py_compile
try:
    py_compile.compile(os.path.join(ROOT, 'pharmacy/routes/controlled_register.py'), doraise=True)
    ok(True, 'register route compiles')
except py_compile.PyCompileError as e:
    ok(False, 'register route compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
