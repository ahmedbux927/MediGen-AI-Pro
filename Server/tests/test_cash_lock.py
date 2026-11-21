"""Cash drawer lock (v87.03): the rule, and checks that every cash path uses it before writing. No MySQL needed.
Run: python tests/test_cash_lock.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services.cash_drawer import lock_message

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

ok(lock_message(True, 'Cash', 500, 'before taking cash for this bill') is None, 'open drawer: cash is allowed')
msg = lock_message(False, 'Cash', 500, 'before taking cash for this bill')
ok(msg is not None and 'drawer is closed' in msg and 'before taking cash for this bill' in msg,
   'closed drawer: cash is refused with the reason and what to do')
ok(lock_message(False, 'Card', 500, 'x') is None, 'card is not affected by the drawer')
ok(lock_message(False, 'Online', 500, 'x') is None, 'online is not affected by the drawer')
ok(lock_message(False, 'Cash', 0, 'x') is None, 'zero cash amount is not blocked (nothing is taken)')
ok(lock_message(False, 'Cash', None, 'x') is None, 'missing amount is not blocked')
ok(lock_message(False, 'Cash', 12.5, 'x') is not None, 'small cash amount is blocked too')

sales = read('pharmacy/routes/sales.py')
lock_at = sales.index('lock = cash_lock_message(CDR.open_session(cur) is not None, payment, bill[')
save_at = sales.index('sale_id = save_sale(cur, session[')
ok(lock_at < save_at, 'live sale: cash lock runs before the sale is saved')
ok("if not offline_sync:" in sales[lock_at - 200:lock_at], 'live sale lock is skipped for offline sync bills')
ok("return redirect(url_for('new_sale'))" in sales[lock_at:lock_at + 400], 'refused sale returns to the sale page')
pay_at = sales.index("lock = cash_lock_message(CDR.open_session(cur) is not None, method, amount")
upd_at = sales.index('UPDATE sales SET paid_amount = paid_amount + %s')
ok(pay_at < upd_at, 'receiving a cash payment on an old bill: lock runs before the update')

exp = read('pharmacy/routes/expenses.py')
ok(exp.index('cash_lock_message(CDR.open_session') < exp.index('eid = repo.insert('),
   'cash expense: lock runs before the expense is written')
ok("paid_via, amount, 'before recording this cash expense')" in exp, 'expense lock names the expense')

pos = read('pharmacy/services/pos.py')
ok(pos.index('cash_lock_message(CDR.open_session') < pos.index('sale_id = save_sale(cur, user_id'),
   'POS bill: lock runs before the bill is saved')
ok("raise BillError(lock)" in pos, 'POS refusal is a clear bill error (shown to the caller)')

import py_compile
for f in ['pharmacy/routes/sales.py', 'pharmacy/routes/expenses.py', 'pharmacy/services/pos.py', 'pharmacy/services/cash_drawer.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f'{f} compiles')
    except py_compile.PyCompileError as e:
        ok(False, f'{f} compiles: {e}')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
