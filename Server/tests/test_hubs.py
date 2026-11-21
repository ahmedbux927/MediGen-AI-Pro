"""Sidebar groups and their hub pages (v87.16). Static checks, no MySQL needed.
Run: python tests/test_hubs.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

hubs = read('pharmacy/routes/hubs.py')
base = read('templates/base.html')
init = read('pharmacy/routes/__init__.py')

ok('from . import hubs' in init, 'hub routes are registered')
ok(os.path.exists(os.path.join(ROOT, 'templates', 'hub.html')), 'hub template exists')

hub_urls = re.findall(r"@app\.route\('(/[^']+)'\)", hubs)
ok(len(hub_urls) == 6, 'six group hub URLs exist (found %d)' % len(hub_urls))
ok(hubs.count('@role_required(') == 6, 'every hub is role-guarded')

# every card points at a real route function
endpoints = set(re.findall(r"'bi-[a-z-]+', '([a-z_]+)'", hubs))
routes_src = ''.join(read(os.path.join('pharmacy', 'routes', f)) for f in os.listdir(os.path.join(ROOT, 'pharmacy', 'routes')) if f.endswith('.py'))
missing = sorted(e for e in endpoints if not re.search(r"def %s\(" % e, routes_src))
ok(endpoints and not missing, 'every hub card points to a real endpoint (missing: %s)' % missing)

# sidebar: nine entries, in the agreed order
order = ["url_for('dashboard')", "url_for('medicines_hub')", "url_for('inventory_hub')", "url_for('sales_hub')", "url_for('purchasing_hub')", "url_for('finance_hub')", "url_for('chatbot')", "url_for('admin_hub')", "url_for('profile')"]
pos = [base.index(k) for k in order]
ok(pos == sorted(pos), 'sidebar entries are in the agreed order')
ok('Product Overview' not in base and 'nav-section">Suppliers' not in base, 'old section names are gone from the sidebar')
ok(base.count('<i class="bi bi-') < 40, 'sidebar has few entries (no long list)')

# Cashier: Sales and Medicines and Inventory only; the rest is Admin or Pharmacist
ok("ALL = ('Admin', 'Pharmacist', 'Cashier')" in hubs and "ADMIN_PH = ('Admin', 'Pharmacist')" in hubs, 'role sets are defined once')
ok('Build v87.23' not in hubs and 'Build v{{ app_version }}' in read('templates/medicines.html'), 'build marker is v87.19')

print('\n%d passed, %d failed' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
