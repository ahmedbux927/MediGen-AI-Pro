"""v88.00: enhancements E1-E5 source contracts (mock suite, no MySQL)."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

# E1 dashboard links to filtered lists
dash = read('templates/dashboard.html')
ok("url_for('medicines', filter='low')" in dash, 'E1: dashboard low-stock card links to the filtered medicines list')
ok("url_for('medicines', filter='out')" in dash, 'E1: dashboard out-of-stock link')
ok("url_for('batches', filter='soon', days=30)" in dash and "days=60" in dash and "days=90" in dash,
   'E1: dashboard expiry buckets link to 30/60/90-day batch lists')
ok("url_for('sales')" in dash and "url_for('reports')" in dash, 'E1: sales and profit cards link onward')
batches = read('pharmacy/routes/batches.py')
ok("days in (30, 60, 90)" in batches, 'E1: batches page honours the days bucket')

# E2 CSV exports: sales, purchases, stock with date range + BOM
rep = read('pharmacy/routes/reports.py')
ok("'purchases'" in rep and 'purchase_orders' in rep, 'E2: purchases CSV export exists')
ok('BETWEEN %s AND %s' in rep, 'E2: exports apply the date range')
lib = read('pharmacy/lib.py')
ok("'\\ufeff'" in lib or '\\ufeff' in lib, 'E2: CSV is UTF-8 with BOM for Excel')

# E3 receipts: both layouts carry shop name, phone and footer
inv = read('templates/invoice.html'); th = read('templates/receipt_thermal.html')
for name, tpl in (('A4 invoice', inv), ('80mm receipt', th)):
    ok('shop.name' in tpl and 'shop.phone' in tpl and 'shop.footer' in tpl,
       f'E3: {name} shows shop name, phone and footer')

# E4/E5 polish assets are wired in
base = read('templates/base.html')
ok('css/app.css' in base and '===== v88-polish.css =====' in read('static/css/app.css'), 'E4: accessibility polish stylesheet is loaded (via the app.css bundle)')
css = read('static/css/v88-polish.css')
ok(':focus-visible' in css and '44px' in css and 'prefers-reduced-motion' in css,
   'E4: visible focus rings, 44px controls, reduced-motion support')
js = read('static/js/v88-utils.js')
ok('mgDebounce' in js and '250' in js, 'E5: debounced search helper (250 ms)')

# E6 friendly error pages with retry
for tpl in ('templates/404.html', 'templates/500.html'):
    ok('mg-retry' in read(tpl), 'E6: retry button on ' + tpl)

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
    _sys.exit(1 if bad else 0)
