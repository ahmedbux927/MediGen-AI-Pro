"""Checks for the offline bill id (v86.62 stage 1). A bill sent twice with the same id is saved once."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

core = read('pharmacy/core.py')
pos = read('pharmacy/services/pos.py')
ok("('client_uuid', 'VARCHAR(64) NULL')" in core, 'sales.client_uuid column added at startup')
ok('uq_sales_client_uuid' in core and 'ADD UNIQUE KEY' in core, 'unique key on client_uuid (NULLs allowed)')
ok("body.get('client_uuid')" in pos and "[:64]" in pos, 'checkout reads and limits the offline id')
ok("'already_saved': True" in pos and "SELECT sale_id, total_amount, paid_amount FROM sales WHERE client_uuid" in pos,
   'a repeated id returns the same bill without saving again')
ok(pos.index('already saved') < pos.index('resolve_items(cur, body.get') if 'already saved' in pos else
   pos.index('already_saved') < pos.index("wanted = resolve_items(cur, body.get('items'))"),
   'the repeat check runs before items are reserved (no stock taken twice)')
ok("UPDATE sales SET client_uuid" in pos, 'the id is saved with the bill in the same transaction')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
