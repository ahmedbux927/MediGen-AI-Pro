"""Step 3 checks: data-access layer (pharmacy/repos). Pure unit tests, no Flask, no MySQL.
Run through tests/run_all.py."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, re
sys.path.insert(0, ROOT)
from pharmacy.repos import medicines as med, catalog as cat

RESULTS = []
def check(name, cond):
    RESULTS.append((name, bool(cond)))

class FakeCur:
    """Records SQL; answers from scripted rows in order."""
    def __init__(self, fetch_rows=None):
        self.calls = []
        self.queue = list(fetch_rows or [])
        self.lastrowid = 77
    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))
    def fetchone(self):
        return self.queue.pop(0) if self.queue else None
    def fetchall(self):
        return self.queue.pop(0) if self.queue else []
    def close(self):
        pass

# ---- paging and filters ----
cur = FakeCur([{'total': 45}, [{'name': 'Panadol'}]])
out = med.list_medicines(cur, '%pan%', 'low', page=9, per=10)
check('paging clamps page to last page (45 rows / 10 per = 5 pages)', out['page'] == 5 and out['pages'] == 5)
check('paging offset = (page-1)*per', out['offset'] == 40)
count_sql, count_params = cur.calls[0]
check('count query carries the low-stock filter', 'stock_quantity <= m.reorder_level' in count_sql)
check('search pattern passed as parameter, not in SQL text',
      count_params == ['%pan%', '%pan%'] and '%pan%' not in count_sql)
rows_sql, rows_params = cur.calls[1]
check('LIMIT/OFFSET are parameters', rows_params[-2:] == [10, 40] and 'LIMIT %s OFFSET %s' in rows_sql)

cur = FakeCur([{'total': 0}, []])
med.list_medicines(cur, '', 'all', page=1, per=15)
check('list always hides deleted medicines (v86.29)', 'm.is_deleted = 0' in cur.calls[0][0])
check('empty result still returns at least 1 page', med.list_medicines(FakeCur([{'total': 0}, []]), '', 'all', 1, 15)['pages'] == 1)

# ---- FIFO batch consumption ----
batches = [{'batch_id': 1, 'quantity': 5}, {'batch_id': 2, 'quantity': 10}, {'batch_id': 3, 'quantity': 7}]
cur = FakeCur([batches])
med.take_from_batches_fifo(cur, 9, 12)
updates = [(s, p) for s, p in cur.calls if s.startswith('UPDATE batches')]
check('FIFO takes whole first batch then part of second', updates == [
    ('UPDATE batches SET quantity = quantity - %s WHERE batch_id=%s', (5, 1)),
    ('UPDATE batches SET quantity = quantity - %s WHERE batch_id=%s', (7, 2))])
check('FIFO select is ordered by expiry first and locks rows',
      'ORDER BY expiry_date ASC' in cur.calls[0][0] and 'FOR UPDATE' in cur.calls[0][0])

cur = FakeCur([batches])
med.take_from_batches_fifo(cur, 9, 0)
check('FIFO with qty 0 touches no batch', not [c for c in cur.calls if c[0].startswith('UPDATE')])

# ---- lookups and writes ----
check('find by name returns None when no row', med.find_medicine_by_name(FakeCur([None]), 'X') is None)
cur = FakeCur([{'medicine_id': 4}])
med.find_medicine_by_name(cur, 'Panadol', exclude_id=4)
check('edit duplicate check excludes own id', cur.calls[0][1] == ('Panadol', 4) and '<> %s' in cur.calls[0][0])

cur = FakeCur()
new_id = med.insert_medicine(cur, {'name': 'A', 'category_id': 1, 'price': 10, 'cost': 5, 'reorder': 3}, 20)
check('insert_medicine returns lastrowid', new_id == 77)
check('insert_medicine binds values in order (barcode empty)', cur.calls[0][1] == ('A', None, 1, 10, 5, 20, 3, None, None))

cur = FakeCur()
med.insert_opening_stock(cur, 77, 2, 20)
check('opening stock row has old 0 and new = stock', cur.calls[0][1] == (77, 2, 20, 20))

cur = FakeCur()
med.delete_medicine(cur, 5)
check('delete uses parameter for id', cur.calls[0] == ('DELETE FROM medicines WHERE medicine_id=%s', (5,)))

cur = FakeCur()
med.export_medicine_rows(cur, [3, 4])
check('export with ids builds one %s per id', cur.calls[0][0].count('%s') == 2 and cur.calls[0][1] == [3, 4])
cur = FakeCur()
med.export_medicine_rows(cur, [])
check('export with no ids has no IN clause', ' IN (' not in cur.calls[0][0])

# ---- stats coerce NULL to 0 ----
s = med.medicine_stats(FakeCur([{'total': None, 'in_stock': None, 'low': None, 'out_count': None}]))
check('stats: NULL sums become 0', s == {'total': 0, 'in_stock': 0, 'low': 0, 'empty': 0})

# ---- catalog ----
cur = FakeCur([{'c': 3}])
check('count medicines in category returns number', cat.count_medicines_in_category(cur, 2) == 3)
check('category exists: found', cat.category_name_exists(FakeCur([{'category_id': 1}]), 'Antibiotic') is True)
check('category exists: not found', cat.category_name_exists(FakeCur([None]), 'Nope') is False)
cur = FakeCur()
cat.insert_customer(cur, 'Ali', '0300', 'a@x.pk', 'Male', 'none')
check('customer insert binds five fields in order', cur.calls[0][1] == ('Ali', '0300', 'a@x.pk', 'Male', 'none'))
cur = FakeCur()
cat.insert_supplier(cur, 'S', '1', 'e', 'addr')
check('supplier insert binds four fields in order', cur.calls[0][1] == ('S', '1', 'e', 'addr'))

# ---- architecture: routes contain no raw SQL any more for these modules ----
SQL_RE = re.compile(r'\b(SELECT|INSERT INTO|UPDATE|DELETE FROM)\b')
for fn in ('medicines.py', 'catalog.py'):
    text = open(_os.path.join(ROOT, 'pharmacy', 'routes', fn), encoding='utf-8').read()
    check(f'routes/{fn} has no raw SQL', not SQL_RE.search(text))
check('repos package has no Flask import',
      not any(re.search(r'^\s*(from|import)\s+flask', open(_os.path.join(ROOT, 'pharmacy', 'repos', f), encoding='utf-8').read(), re.M)
              for f in ('medicines.py', 'catalog.py')))

# ---- report ----
failed = [n for n, ok in RESULTS if not ok]
for n, ok in RESULTS:
    print(('PASS ' if ok else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed:
    sys.exit(1)
