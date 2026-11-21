"""Inventory rules (backend track, B7): expiry buckets, low-stock severity, purchase suggestions. Pure.
Run: python tests/test_inventory.py
"""
import os, sys
from datetime import date, timedelta
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import inventory as I

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

T = date(2026, 10, 23)
def batch(days, qty=5, mid=1, name='Panadol'):
    return {'medicine_id': mid, 'name': name, 'batch_number': f'B{days}', 'expiry_date': T + timedelta(days=days), 'quantity': qty}

b = I.expiry_buckets([batch(-3), batch(0), batch(10), batch(30), batch(31), batch(60), batch(61), batch(90), batch(91), batch(15, qty=0)], T)
ok([r['days_left'] for r in b['expired']] == [-3], 'expired stock listed (3 days ago)')
ok([r['days_left'] for r in b['0-30 days']] == [0, 10, 30], 'expiring today, in 10 and in 30 days go in 0-30')
ok([r['days_left'] for r in b['31-60 days']] == [31, 60], '31 and 60 days go in 31-60')
ok([r['days_left'] for r in b['61-90 days']] == [61, 90], '61 and 90 days go in 61-90')
ok(sum(len(v) for v in b.values()) == 8, 'batch after 90 days and empty batch are left out')

low = I.low_stock([
    {'medicine_id': 1, 'name': 'A', 'stock_quantity': 0, 'reorder_level': 10},
    {'medicine_id': 2, 'name': 'B', 'stock_quantity': 4, 'reorder_level': 10},
    {'medicine_id': 3, 'name': 'C', 'stock_quantity': 8, 'reorder_level': 10},
    {'medicine_id': 4, 'name': 'D', 'stock_quantity': 11, 'reorder_level': 10}])
ok([(r['name'], r['severity']) for r in low] == [('A', 'out'), ('B', 'critical'), ('C', 'low')],
   'low stock: out, critical (below half), low (at reorder); above reorder left out, sorted by severity')
ok(I.low_stock([{'medicine_id': 9, 'name': 'Z', 'stock_quantity': 5, 'reorder_level': 5}])[0]['severity'] == 'low',
   'stock exactly at the reorder level is low, not critical')

sug = I.purchase_suggestions([
    {'medicine_id': 1, 'name': 'A', 'stock_quantity': 0, 'reorder_level': 10, 'cost_price': 50},
    {'medicine_id': 2, 'name': 'B', 'stock_quantity': 4, 'reorder_level': 10, 'cost_price': 20},
    {'medicine_id': 3, 'name': 'C', 'stock_quantity': 8, 'reorder_level': 10, 'cost_price': 5}],
    {1: (7, 'Sami Traders'), 2: (7, 'Sami Traders')})
ok(sug[7]['supplier'] == 'Sami Traders' and sug[7]['estimated_cost'] == round(50 * 20 + 20 * 16, 2),
   'suggested order grouped by last supplier, cost estimated (20 x 50 + 16 x 20)')
ok(sug['none']['supplier'] == 'No supplier history' and sug['none']['items'][0]['order_qty'] == 12,
   'no purchase history goes under "No supplier history"; order up to twice reorder (20 - 8 = 12)')
ok(I.purchase_suggestions([{'medicine_id': 5, 'name': 'E', 'stock_quantity': 30, 'reorder_level': 10, 'cost_price': 1}], {}) == {},
   'items with enough stock get no suggestion')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
