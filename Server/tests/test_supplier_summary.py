"""Static checks for the Supplier Summary (v86.47). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/supplier_ledger.py')
repo = read('pharmacy/repos/supplier_ledger.py')
tpl = read('templates/supplier_summary.html')
ok("@app.route('/supplier-summary')" in route and "role_required('Admin')" in route, 'route exists, Admin only like Purchase')
ok('@guarded' in route, 'supplier summary route is guarded')
ok('UPDATE ' not in repo and 'DELETE ' not in repo and repo.count('INSERT ') == 1 and 'def insert_payment' in repo, 'supplier repo only writes a payment row, nothing else')
ok("status = 'Received'" in repo, 'bought amount counts only received orders')
ok("from . import supplier_ledger" in read('pharmacy/routes/__init__.py'), 'route registered')
ok("'supplier_summary'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'sidebar link added')
ok('{% extends' in tpl and 'Owed' in tpl, 'template extends base and shows owed')
ok("supplier_payments" in read('pharmacy/core.py') and 'CREATE TABLE IF NOT EXISTS supplier_payments' in read('pharmacy/core.py'), 'payments table created at startup')
pay = route.split('def supplier_payment')[1]
ok("role_required('Admin')" in route.split('def supplier_payment')[0].split('@app.route')[-1] and '@guarded' in route.split('def supplier_payment')[0], 'payment route Admin only and guarded')
ok("paid_on > date.today().isoformat()" in pay and "amount <= 0" in pay, 'payment rejects zero amount and future date')
ok("repo.insert_payment" in pay and "audit(cur, 'supplier.payment'" in pay, 'payment is saved and audited')
ok('csrf_token' in tpl, 'payment form has csrf token')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
