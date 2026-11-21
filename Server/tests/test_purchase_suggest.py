"""v86.24: purchase suggestion logic (checked with a stub cursor; no MySQL needed)."""
import ast, math, os, sys
from decimal import Decimal

ROOT = os.path.join(os.path.dirname(__file__), '..')
src = open(os.path.join(ROOT, 'pharmacy', 'routes', 'purchase_suggest.py'), encoding='utf-8').read()
tree = ast.parse(src)
ns = {'math': math, 'SALES_DAYS': 30, 'COVER_DAYS': 30, 'ALERT_DAYS': 14}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == '_suggestion_rows':
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'x', 'exec'), ns)
fn = ns['_suggestion_rows']

class Cur:
    def __init__(self, rows): self.rows = rows
    def execute(self, sql, params=None): pass
    def fetchall(self): return self.rows

def m(name, stock, reorder, sold, cost='10'):
    return {'name': name, 'stock_quantity': stock, 'reorder_level': reorder, 'cost_price': Decimal(cost), 'sold': sold}

fails = []
def ok(c, label):
    print(('PASS ' if c else 'FAIL ') + label)
    if not c: fails.append(label)

rows = fn(Cur([
    m('Low one', 5, 20, 0),          # low stock, no sales: order up to reorder level
    m('Fast', 50, 10, 300),          # 10/day -> 5 days left: order 30 days = 300 - 50 = 250
    m('Fine', 500, 10, 30),          # 1/day -> 500 days: not listed
    m('Dead', 100, 10, 0),           # no sales, stock fine: not listed
]))
names = [r['name'] for r in rows]
ok('Fine' not in names and 'Dead' not in names, 'healthy and dead stock are not listed')
low = next(r for r in rows if r['name'] == 'Low one')
ok(low['qty'] == 15 and low['low'] is True, 'low item: qty up to reorder level (20 - 5 = 15)')
fast = next(r for r in rows if r['name'] == 'Fast')
ok(fast['qty'] == 250 and fast['days_left'] == 5.0, 'fast item: 30 days cover (300 - 50 = 250), 5 days left')
ok(names[0] == 'Fast', 'most urgent (fewest days left) comes first; no-sale items last')
ok(fast['est_cost'] == 2500.0, 'estimated cost = qty x cost price (250 x 10)')
ok(low['days_left'] is None, 'no sales gives days_left None')
print('ALL PASS' if not fails else f'{len(fails)} FAILED')
sys.exit(1 if fails else 0)
