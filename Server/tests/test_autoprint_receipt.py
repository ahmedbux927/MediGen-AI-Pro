"""v71: a completed POS sale opens the 80 mm receipt with ?print=1 (auto print).
Source checks only (no MySQL). Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
tpl = open(_os.path.join(ROOT, 'templates', 'receipt_thermal.html'), encoding='utf-8').read()
ok("redirect(url_for('invoice_thermal', sale_id=sale_id, print=1))" in src, 'completed POS sale redirects to the thermal receipt with print=1')
ok("redirect(url_for('invoice', sale_id=sale_id))" not in src.split('def new_sale')[1].split('@app.route')[0], 'POS no longer lands on the A4 invoice after saving')
ok("get('print') === '1'" in tpl and 'window.print()' in tpl, 'receipt page prints itself when print=1')
ok('onclick="window.print()"' in tpl, 'manual Print button still exists')
failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
