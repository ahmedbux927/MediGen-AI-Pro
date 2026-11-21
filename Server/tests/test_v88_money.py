"""v88.00: B8 - money and stock rules that were missing tests.
Mock suite (no MySQL). Run through tests/run_all.py.

Covered:
  1. 0% tax identity: tax is 0 and total = subtotal - discount.
  2. Tax-free half-paisa rounding: 15% of Rs 33.33 is Rs 4.9995, billed as Rs 5.00.
  3. Stock never goes negative: reserve_lines refuses qty > stock unless allow_short.
  4. allow_short (offline contract only) sells the uncovered units with batch NULL.
  5. A return restores the SAME batch_id the sale item came from.
"""
import os as _os, sys as _sys, types
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

from pharmacy.services import sales as S

# ---- 1 + 2: calculate_bill rounding ----
b = S.calculate_bill(250.0, 10, False, None, 1, 'Admin', 10, 0)
ok(b['tax'] == 0 and b['total'] == 240.0, '0% tax identity: tax 0, total = subtotal - discount')
b = S.calculate_bill(33.33, 15, True, None, 1, 'Admin', 10, 0)
ok(b['discount'] == 5.0, 'half-paisa discount 4.9995 rounds to Rs 5.00')
ok(b['tax'] == 0 and b['total'] == 28.33, 'tax-free total after half-paisa rounding is 28.33')
b = S.calculate_bill(100.0, 0, False, None, 1, 'Admin', 10, 5)
ok(b['tax'] == 5.0 and b['total'] == 105.0, '5% tax is exact on a round bill')

# ---- 3 + 4: stock never negative ----
class FakeCur:
    """One medicine (stock 5, price 10) with one batch of 5 units (batch_id 7)."""
    def __init__(self): self.sql = ''; self.rows = []
    def execute(self, sql, p=None):
        self.sql = ' '.join(sql.split())
        if 'FROM medicines' in self.sql:
            self.rows = [{'name': 'Panadol', 'price': 10.0, 'stock_quantity': 5}]
        elif 'COUNT(*) AS n FROM batches' in self.sql:
            self.rows = [{'n': 1}]
        elif 'FROM batches' in self.sql:
            self.rows = [{'batch_id': 7, 'quantity': 5}]
        else:
            self.rows = []
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows
    def close(self): pass

try:
    S.reserve_lines(FakeCur(), {1: 6})
    ok(False, 'qty 6 with stock 5 is refused (stock never negative)')
except S.BillError:
    ok(True, 'qty 6 with stock 5 is refused (stock never negative)')
lines, subtotal, _names = S.reserve_lines(FakeCur(), {1: 6}, allow_short=True)
flat = [part for _mid, _price, parts in lines for part in parts]
ok((7, 5) in flat and (None, 1) in flat, 'allow_short sells 5 from batch 7 and 1 short with batch NULL')
lines, subtotal, _names = S.reserve_lines(FakeCur(), {1: 5})
ok(lines[0][2] == [(7, 5)] and subtotal == 50.0, 'exact-stock sale uses batch 7 only')

# ---- 5: return restores the same batch ----
src = read('pharmacy/routes/sales.py')
ok("it['batch_id']" in src and 'INSERT INTO sale_return_items' in src,
   'return row is written with the sale item batch_id')
ok('UPDATE batches SET quantity = quantity + %s WHERE batch_id=%s' in src,
   'return adds the quantity back to that same batch')
lib = read('pharmacy/lib.py')
ok('si.batch_id' in lib, '_return_items reads batch_id from the original sale item')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
    _sys.exit(1 if bad else 0)
