"""Checks for the dashboard medicine card (v86.67). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()
dash = read('pharmacy/routes/dashboard.py')
tpl = read('templates/dashboard.html')
ok("total_meds = sections['medicines']['items']" in dash, 'Total medicines card counts the Medicines section only')
ok("Section records" in tpl and "rec.sections" in tpl and "s['key']" in tpl, 'every section has its own row and card (v86.76)')
ok(read('pharmacy/services/product_sections.py').count("'medicines'") > 0, 'Medicines is a section key')
ok("low_by_section" in dash and "_r['section'] = _labels.get(_k, _k)" in dash, 'low stock is counted and named for every section')
ok('stock_quantity <= reorder_level' in dash and 'FROM medicines' in dash, 'low stock uses the same rule as the Medicines page')
ok("s['low_items']" in tpl and "Low stock" in tpl and "s['low']" in tpl, 'dashboard shows per-section low stock items and count')

ok("expiring_by_section" in dash and "_e['section'] = _elabels.get(_k, _k)" in dash, 'expiring batches are counted and named for every section')
ok("expiring_total = len(expiring_all)" in dash and 'v_expiring_soon LIMIT 5' not in dash, 'expiring list uses all sections, not the Medicines-only view')
ok("s['expiring_items']" in tpl and 'Expiring within 90 days' in tpl, 'dashboard shows per-section expiring batches (v86.76)')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
