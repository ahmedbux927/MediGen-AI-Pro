"""v86.37: hidden (deleted) medicines must be left out of every list, export, search and report.
Static check of the queries that read the medicines table for lists. Run through run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

ok("is_deleted = 0" in read('pharmacy/routes/api.py'), 'API medicine list hides deleted items')
ok("is_deleted = 0" in read('pharmacy/services/agent_tools.py') and read('pharmacy/services/agent_tools.py').count('is_deleted') >= 3,
   'agent search, low stock and expiring hide deleted items')
ok("is_deleted = 0" in read('pharmacy/services/drip_report.py'), 'drip report hides deleted items')
ok("is_deleted = 0" in read('pharmacy/services/stock_count.py'), 'stock count hides deleted items')
ok("m.is_deleted = 0 AND m.stock_quantity > 0" in read('pharmacy/routes/reports.py'), 'slow movers report hides deleted items')
ok("FROM medicines m WHERE m.is_deleted = 0" in read('pharmacy/routes/purchase_suggest.py'), 'purchase suggestions hide deleted items')
ok("WHERE m.is_deleted = 0 GROUP BY" in read('pharmacy/routes/batches.py'), 'batch mismatch count hides deleted items')
ok("m.is_deleted = 0" in read('pharmacy/repos/medicines.py') and 'if ids:' in read('pharmacy/repos/medicines.py'), 'CSV export hides deleted items')
ok("m.is_deleted = 0 AND b.quantity > 0" in read('pharmacy/lib.py'), 'expiry rows hide deleted items')
ok('def ensure_hidden_views' in read('pharmacy/core.py') and 'is_deleted = 0 AND stock_quantity' in read('pharmacy/core.py'),
   'dashboard views are re-created without deleted items at startup')
ok('is_deleted = 0 AND stock_quantity <= reorder_level' in read('database/schema.sql'), 'schema.sql views match')

if __name__ == '__main__':
    fails = [m for m, good in RESULTS if not good]
    for m, good in RESULTS:
        print(('PASS ' if good else 'FAIL ') + m)
    print(f"\nTOTAL: {len(RESULTS)-len(fails)} passed, {len(fails)} failed")
