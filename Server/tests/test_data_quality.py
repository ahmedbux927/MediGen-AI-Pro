"""Static checks for the Data Quality report (v86.46). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/data_quality.py')
repo = read('pharmacy/repos/data_quality.py')
tpl = read('templates/data_quality.html')
ok("@app.route('/data-quality')" in route and "role_required('Admin', 'Pharmacist')" in route, 'route exists for Admin and Pharmacist')
ok('@guarded' in route, 'data quality route is guarded')
ok('UPDATE ' not in repo and 'DELETE ' not in repo and 'INSERT ' not in repo, 'data quality repo is read only')
ok('is_deleted = 0' in repo and repo.count('is_deleted = 0') >= 7, 'every medicine query skips deleted medicines')
ok("from . import data_quality" in read('pharmacy/routes/__init__.py'), 'route registered in routes/__init__.py')
ok("'data_quality'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'sidebar link added')
ok('{% extends' in tpl and 'score' in tpl, 'template extends base and shows score')
ok('def duplicate_barcodes' in repo and 'GROUP BY barcode' in repo and 'is_deleted = 0' in repo.split('def duplicate_barcodes')[1], 'barcode duplicate check skips deleted items')
ok("('barcode', 'Same barcode on two items'" in route and "key in ('duplicate', 'repeat_cat', 'barcode')" in route, 'barcode check is listed and not counted as a single item')
ok("key == 'barcode'" in tpl, 'template shows barcode duplicates')
pr = read('pharmacy/routes/products.py')
ok("med['dosage_form']" not in pr, 'product routes read dosage_form safely (no crash if the column is missing)')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
