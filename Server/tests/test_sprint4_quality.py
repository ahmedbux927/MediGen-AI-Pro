"""
Sprint 4 checks: dashboard chart accessibility and responsive markup.
Run: python tests/test_sprint4_quality.py
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)


PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()

tpl = read('templates/dashboard.html')
ok('role="img"' in tpl and 'aria-labelledby="salesChartTitle"' in tpl, 'sales chart is exposed as an image with a labelled title')
ok("Best sellers (30 days)" in tpl and "s['top']" in tpl, 'top-selling is listed for every section (no chart)')
ok(tpl.count('<table class="sr-only"') == 1, 'the sales chart has a screen-reader data table')
js = read('static/js/charts.js')
ok('maintainAspectRatio: false' in js and 'maintainAspectRatio: true' not in js.split('weekBars')[0], 'charts fill a fixed-height box (responsive)')
ok('No sales in the last 7 days yet.' in js and 'No sales recorded yet.' in js, 'empty states are shown instead of blank charts')
ok("'#a85f0a', '#5b6b84'" in js, 'low-contrast slice and label colours replaced')
css = read('static/css/pages.css')
ok('.sr-only' in css and '.chart-body' in css and '@media (max-width: 576px)' in css, 'CSS for sr-only, chart box and phone layout present')
ok('prefers-reduced-motion' in css, 'reduced-motion preference handled')

route = read('pharmacy/routes/dashboard.py')
ok('sales_rows=' in route and 'med_rows=' in route, 'route passes table rows to the template')

print(f"\nTOTAL: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
