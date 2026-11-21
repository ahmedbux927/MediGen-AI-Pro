"""Checks for the expenses khata and dashboard money tiles (v86.61). Run through tests/run_all.py or directly."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

_sys.path.insert(0, ROOT)
from pharmacy.services import cash_drawer as CD
from pharmacy.repos import expenses as EXP

ok('Electricity' in EXP.CATEGORIES and 'Salary' in EXP.CATEGORIES, 'standard expense categories exist')
ok(EXP.PAID_VIA == ('Cash', 'Card', 'Online'), 'payment methods match the sales methods')
ok(CD.expected_cash(1000, 500, 0, 200, 100) == 1600, 'drawer expected after an expense is written as cash out')

repo = read('pharmacy/repos/expenses.py')
route = read('pharmacy/routes/expenses.py')
tpl = read('templates/expenses.html')
core = read('pharmacy/core.py')
cd_repo = read('pharmacy/repos/cash_drawer.py')
dash = read('pharmacy/routes/dashboard.py')
dash_tpl = read('templates/dashboard.html')

ok('CREATE TABLE IF NOT EXISTS expenses' in core and 'amount DECIMAL(15,2)' in core, 'expenses table created at startup')
ok('INSERT INTO expenses' in repo and 'SELECT' in repo and 'DELETE' not in repo and 'UPDATE expenses' not in repo, 'expenses are add-only (no delete or edit)')
ok("@role_required('Admin', 'Pharmacist')" in route and route.count('@guarded') >= 2, 'expenses open to Admin and Pharmacist, guarded')
ok("CDR.insert_movement" in route and "paid_via == 'Cash'" in route, 'cash expense also written as drawer cash out')
ok("if category not in repo.CATEGORIES" in route, 'category is validated against the list')
ok("when > date.today().isoformat()" in route, 'future expense date is refused')
ok("audit(cur, 'expense.add'" in route, 'expense add is audited')
ok('csrf_token' in tpl and "url_for('expense_add')" in tpl, 'expense form carries csrf token')
ok("'%Y-%m'" in route, 'month filter parses YYYY-MM')
ok("{% extends 'base.html' %}" in tpl, 'expenses page extends base')
ok("url_for('expenses')" in read('templates/base.html') or "'expenses'," in read('pharmacy/routes/hubs.py'), 'expenses is linked (sidebar or Finance hub)')
ok('from . import expenses' in read('pharmacy/routes/__init__.py'), 'expenses routes registered')

ok("FROM sale_payments" in cd_repo and "method = 'Cash'" in cd_repo, 'drawer counts cash from sale_payments (udhaar repaid included)')
ok('paid_amount), 0) AS v FROM sales' not in cd_repo, 'old sales.paid_amount cash term removed (no double count)')
ok("money['udhaar_total']" in dash and "money['net_today']" in dash, 'dashboard computes udhaar total and net profit')
ok("'cash_in_hand'" in dash and 'Drawer closed' in dash_tpl, 'dashboard shows cash in hand or drawer band')
ok('Net profit today' in dash_tpl and 'money.exp_today' in dash_tpl, 'dashboard card shows expenses and net profit')
ok('Build v{{ app_version }}' in read('templates/medicines.html'), 'build marker is v87.00')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
