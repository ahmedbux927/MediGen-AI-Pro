"""Sales rules in pharmacy/services/sales.py (backend track, B3). Pure, no Flask, no MySQL.
Run: python tests/test_services_sales.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import sales as S

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def raises(fn, msg_part, label):
    try:
        fn(); ok(False, label)
    except S.BillError as e:
        ok(msg_part in str(e), label)

# ---- reading the form ----
ok(S.read_lines(['3', '1', '3'], ['2', '5', '1']) == {3: 3, 1: 5}, 'repeated medicine joined, quantities added')
ok(S.read_lines(['', '4', '5'], ['', '2', '0']) == {4: 2}, 'blank lines and zero quantities ignored')
raises(lambda: S.read_lines(['', ''], ['', '']), 'at least one medicine', 'empty bill is refused')
raises(lambda: S.read_lines(['1x'], ['1']), 'Invalid medicine', 'non-numeric medicine id refused')
raises(lambda: S.read_lines(['1'], ['100001']), 'too large', 'quantity above the limit refused')
raises(lambda: S.read_lines([str(i) for i in range(1, 102)], ['1'] * 101), 'at most 100', 'more than 100 medicines refused')

# ---- FIFO batches ----
class Cur:
    def __init__(self, meds, batches):
        self.meds, self.batches, self.last = meds, batches, None
    def execute(self, sql, p=None):
        self.last = (' '.join(sql.split()), p)
    def fetchone(self):
        sql, p = self.last
        if sql.startswith('SELECT name, price, stock_quantity'):
            return self.meds.get(p[0])
        if sql.startswith('SELECT COUNT(*) AS n FROM batches'):
            return {'n': len(self.batches.get(p[0], []))}
        return None
    def fetchall(self):
        return list(self.batches.get(self.last[1][0], []))

MEDS = {1: {'name': 'Panadol', 'price': 100, 'stock_quantity': 60}}
BATCHES = {1: [{'batch_id': 11, 'quantity': 20}, {'batch_id': 12, 'quantity': 40}]}
lines, sub, names = S.reserve_lines(Cur(MEDS, BATCHES), {1: 30})
ok(lines == [(1, 100.0, [(11, 20), (12, 10)])] and sub == 3000.0 and names == ['Panadol'],
   'oldest batch first: 20 from batch 11, 10 from batch 12')
raises(lambda: S.reserve_lines(Cur(MEDS, {1: []}), {1: 70}), 'Insufficient stock', 'more than stock refused')
raises(lambda: S.reserve_lines(Cur({}, {}), {9: 1}), 'no longer exists', 'medicine deleted meanwhile refused')
lines2, _, _ = S.reserve_lines(Cur(MEDS, {}), {1: 5})
ok(lines2 == [(1, 100.0, [(None, 5)])], 'medicine without batch records sells with batch NULL')
raises(lambda: S.reserve_lines(Cur({1: {'name': 'Brufen', 'price': 50, 'stock_quantity': 30}},
                                   {1: [{'batch_id': 21, 'quantity': 5}]}), {1: 10}),
       'Only 5 unexpired', 'expired stock is not sold, message says how many can be sold')

# ---- bill maths ----
b = S.calculate_bill(1000.0, 10, True, None, None, 'Admin', None, 10.0)
ok(b == {'discount': 100.0, 'tax': 90.0, 'total': 990.0, 'paid': 990.0}, '10% off 1000, 10% tax: total 990, paid in full')
b = S.calculate_bill(1000.0, 50, False, None, None, 'Admin', None, 0.0)
ok(b['discount'] == 50.0 and b['total'] == 950.0, 'discount in rupees')
b = S.calculate_bill(3000.0, 0, False, 1000.0, 7, 'Admin', None, 0.0)
ok(b['paid'] == 1000.0 and b['total'] == 3000.0, 'udhaar with a customer: part paid')
raises(lambda: S.calculate_bill(3000.0, 0, False, 1000.0, None, 'Admin', None, 0.0), 'needs a customer',
       'udhaar without a customer refused')
raises(lambda: S.calculate_bill(100.0, -1, False, None, None, 'Admin', None, 0.0), 'cannot be negative', 'negative discount refused')
raises(lambda: S.calculate_bill(100.0, 101, True, None, None, 'Admin', None, 0.0), 'more than 100%', 'discount above 100% refused')
raises(lambda: S.calculate_bill(100.0, 200, False, None, None, 'Admin', None, 0.0), 'more than the bill', 'discount above the bill refused')
raises(lambda: S.calculate_bill(1000.0, 20, True, None, None, 'Cashier', 10, 0.0), 'at most 10%', 'cashier above the limit refused')
b = S.calculate_bill(1000.0, 10, True, None, None, 'Cashier', 10, 0.0)
ok(b['discount'] == 100.0, 'cashier at the limit is allowed')
raises(lambda: S.calculate_bill(1000.0, 0, False, 1500.0, 1, 'Admin', None, 0.0), 'between 0 and the total', 'paid above total refused')
raises(lambda: S.calculate_bill(1000.0, 0, False, -5.0, 1, 'Admin', None, 0.0), 'between 0 and the total', 'negative payment refused')
b = S.calculate_bill(1000.0, 0, False, 999.996, 1, 'Admin', None, 0.0)
ok(b['paid'] == b['total'] or abs(b['total'] - b['paid']) <= S.TOLERANCE, 'half a paisa short counts as paid in full')

# ---- guard claim ----
class GuardCur:
    def __init__(self, dup): self.dup, self.sqls = dup, []
    def execute(self, sql, p=None):
        self.sqls.append(sql)
        if self.dup and sql.startswith('INSERT INTO sale_guard'):
            raise type('E', (Exception,), {})(1062, 'dup')
ok(S.claim_guard(GuardCur(False), 'x' * 64, 1) is True, 'new bill is claimed')
ok(S.claim_guard(GuardCur(True), 'x' * 64, 1) is False, 'repeat bill is refused, not raised')
try:
    class Boom(Exception): pass
    class Bad(GuardCur):
        def execute(self, sql, p=None):
            if sql.startswith('INSERT INTO sale_guard'): raise Boom(1452, 'other')
            super().execute(sql, p)
    S.claim_guard(Bad(False), 'x', 1); ok(False, 'other database errors are raised')
except Boom:
    ok(True, 'other database errors are raised')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
