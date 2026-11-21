"""Checks for the same-name-and-strength duplicate error (v86.54). Run through tests/run_all.py or directly.
The repo function is run against a tiny fake cursor, so no database is needed."""
import os as _os, re
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

repo_src = read('pharmacy/repos/medicines.py')
med = read('pharmacy/routes/medicines.py')
prod = read('pharmacy/routes/products.py')

# run the real find_same_product against a fake table
ns = {}
fn_src = repo_src[repo_src.index('def find_same_product'):repo_src.index('def duplicate_message')]
exec(fn_src, ns)
class Cur:
    def __init__(self, rows): self.rows = rows; self.params = None
    def execute(self, sql, params=()):
        self.sql = sql; self.params = list(params)
    def fetchone(self):
        name, strength, mid, deleted = self.params[0], self.params[1], None, None
        for r in self.rows:
            excl = self.params[2] if len(self.params) > 2 else None
            if r['is_deleted']: continue
            if r['name'].strip().lower() != name.strip().lower(): continue
            if (r['strength'] or '').strip().lower() != strength.strip().lower(): continue
            if excl is not None and r['medicine_id'] == excl: continue
            return {'medicine_id': r['medicine_id'], 'name': r['name'], 'strength': r['strength']}
        return None
rows = [
    {'medicine_id': 1, 'name': 'Panadol', 'strength': '500 mg', 'is_deleted': 0},
    {'medicine_id': 2, 'name': 'Panadol', 'strength': None, 'is_deleted': 0},
    {'medicine_id': 3, 'name': 'Brufen', 'strength': '', 'is_deleted': 1},
]
find = ns['find_same_product']
ok(find(Cur(rows), 'panadol', '500 mg') is not None, 'same name and same strength is a duplicate (case ignored)')
ok(find(Cur(rows), 'Panadol', '120 mg') is None, 'same name with a different strength is allowed')
ok(find(Cur(rows), 'Panadol', None) is not None, 'blank strength matches blank strength')
ok(find(Cur(rows), 'Panadol', '500 mg', exclude_id=1) is None, 'editing the same item does not count as a duplicate')
ok(find(Cur(rows), 'Brufen', '') is None, 'deleted (hidden) items do not block a new one')
ok('is_deleted = 0' in fn_src, 'query skips deleted items')
ok("def duplicate_message" in repo_src and 'was not saved' in repo_src, 'clear duplicate message exists')
ok(prod.count('repo.find_same_product') == 2, 'section add and section edit both check duplicates')
ok(med.count('repo.find_same_product') == 2, 'medicines add and edit both check duplicates')
ok("flash(repo.duplicate_message" in med and "'danger')" in med, 'medicines duplicate is an error (danger), not a warning')
ok(not re.search(r"already in the list.*'warning'", prod) and "'This product is already in the list.'" not in prod, 'old warning text removed from section add')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
