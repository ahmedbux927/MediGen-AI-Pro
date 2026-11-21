"""Offline assets: templates load Bootstrap, icons and Chart.js from static/vendor when present,
and the list in scripts/fetch_assets.py matches every local path the templates use.
Static checks only. Run: python tests/test_offline_assets.py"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond: PASS += 1; print('PASS', label)
    else: FAIL += 1; print('FAIL', label)
def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh: return fh.read()

lib = read('pharmacy/lib.py')
ok('def _vendor_asset(local_rel, cdn_url):' in lib and "'vendor_asset'" in lib, 'vendor_asset helper is registered for templates')
ok("os.path.isfile(path)" in lib and "url_for('static', filename='vendor/'" in lib, 'helper uses the local file when it exists')

used = set()
for name in ['base.html', 'dashboard.html', 'reports.html', '404.html', '500.html', 'invoice.html', 'prescription_receipt.html']:
    t = read(os.path.join('templates', name))
    found = re.findall(r"vendor_asset\('([^']+)', '(https://[^']+)'\)", t)
    ok(found != [], f'{name} loads its CSS/JS through vendor_asset')
    used.update(local for local, _ in found)
    bare = re.sub(r"\{\{ vendor_asset\('[^']+', '[^']+'\) \}\}", '', t)
    ok('cdn.jsdelivr.net' not in bare, f'{name} has no bare CDN link outside vendor_asset')

fetch = read('scripts/fetch_assets.py')
targets = set(re.findall(r"\('[^']+', '([^']+)'\)", fetch))
ok(used, 'templates list at least one local asset')
for local in sorted(used):
    ok(local in targets, f'fetch_assets.py downloads {local}')

print(f"\nTOTAL: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
