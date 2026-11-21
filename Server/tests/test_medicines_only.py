"""Static checks: the Medicines page shows only the Medicines section (v86.53). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/medicines.py')
body = route.split('def medicines():')[1].split('@app.route')[0]
ok("PS.section_for(r.get('dosage_form')) == 'medicines'" in body, 'Medicines list keeps only the medicines section')
ok(body.count("PS.section_for(r.get('dosage_form')) == 'medicines'") >= 2, 'stats use the same section filter as the list')
ok("listing['total'] = len(listing['rows'])" in body, 'count shown matches the filtered list')
ok("from pharmacy.services import product_sections as PS" in route or "import product_sections as PS" in route
   or "product_sections as PS" in read('pharmacy/core.py') + read('pharmacy/lib.py') or 'PS.section_for' in route, 'PS helper available to the route')
ok('barcode_map' in body, 'barcode check still covers all sections (duplicate barcodes still warned)')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
