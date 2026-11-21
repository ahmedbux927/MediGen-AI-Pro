"""Double-submit guard (backend track, B1): fingerprint rules, pure, no MySQL needed.
Run: python tests/test_sale_guard.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services.sale_guard import sale_fingerprint, is_duplicate_key, DUPLICATE_WINDOW_SECONDS, PURGE_SQL

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def fp(**kw):
    base = dict(user_id=1, customer_id=None, payment='Cash', rx_id=None, wanted={3: 2, 7: 1},
                discount='0', discount_type='amount', paid='')
    base.update(kw)
    return sale_fingerprint(base['user_id'], base['customer_id'], base['payment'], base['rx_id'], base['wanted'],
                            base['discount'], base['discount_type'], base['paid'])

ok(fp() == fp(), 'same bill gives the same fingerprint')
ok(fp(wanted={7: 1, 3: 2}) == fp(), 'item order does not change the fingerprint')
ok(fp(wanted={3: 3, 7: 1}) != fp(), 'a different quantity is a different bill')
ok(fp(wanted={3: 2}) != fp(), 'a different item list is a different bill')
ok(fp(user_id=2) != fp(), 'the same bill from another user is a different bill')
ok(fp(customer_id=5) != fp(), 'a different customer is a different bill')
ok(fp(payment='Card') != fp(), 'a different payment method is a different bill')
ok(fp(discount='10') != fp(), 'a different discount is a different bill')
ok(fp(paid='500') != fp(), 'a different amount paid is a different bill')
ok(len(fp()) == 64, 'fingerprint is a 64-character SHA-256')
ok(DUPLICATE_WINDOW_SECONDS == 10, 'window is 10 seconds')
ok('INTERVAL 10 SECOND' in PURGE_SQL and PURGE_SQL.startswith('DELETE FROM sale_guard'), 'purge removes only rows older than the window')

class E(Exception):
    pass
ok(is_duplicate_key(E(1062, 'Duplicate entry')), 'MySQL error 1062 is a duplicate')
ok(not is_duplicate_key(E(1452, 'foreign key')), 'other MySQL errors are not treated as duplicates')
ok(not is_duplicate_key(RuntimeError('x')), 'plain errors are not treated as duplicates')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
