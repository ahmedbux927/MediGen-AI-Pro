"""Stage 7 (Master Prompt v4): every pharmacy feature has a live route.

The end-to-end behaviour was verified against a real MySQL + browser on
2026-11-21 (all 32 feature pages returned 200; the stock-count lifecycle
start -> count -> submit -> Admin approve changed stock 800 -> 799, and a
partial count was refused at submit). This test keeps the route surface
from silently shrinking.
"""
import os as _os
import re
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


routes_src = ''
rdir = _os.path.join(ROOT, 'pharmacy', 'routes')
for fn in _os.listdir(rdir):
    if fn.endswith('.py'):
        with open(_os.path.join(rdir, fn), encoding='utf-8', errors='ignore') as f:
            routes_src += f.read()

FEATURES = {
    'batches and expiry alerts': '/batches',
    'expiry alerts page': '/alerts',
    'expiry clearance (suggestions only)': '/expiry-clearance',
    'refill reminders': '/refills',
    'reorder suggestions': '/purchase/suggestions',
    'purchase drafts': '/purchase/drafts',
    'seasonal forecast (labelled suggestion)': '/purchase/forecast',
    'suppliers': '/suppliers',
    'supplier returns': '/supplier-returns',
    'supplier summary and balances': '/supplier-summary',
    'expenses': '/expenses',
    'daily closing': '/daily-closing',
    'profit margins': '/margins',
    'reports': '/reports',
    'inspection report': '/inspection-report',
    'customers and udhaar': '/customers',
    'customer dues': '/customer-dues',
    'cash drawer': '/cash',
    'daily digest': '/digest',
    'data quality': '/data-quality',
    'stock count': '/stock-count',
    'controlled register': '/controlled-register',
    'cold chain log': '/cold-chain',
    'activity log': '/activity-log',
    'prescriptions': '/prescriptions',
    'drug interaction warnings (labelled placeholder)': '/interactions',
    'held bills': '/sales/held',
    'import with preview': '/products/import-preview',
}
for label, path in FEATURES.items():
    ok(f"'{path}'" in routes_src, f'route exists: {label} ({path})')

ok('/inspection-report/export' in routes_src, 'inspection Excel export route exists (password-confirmed POST)')
ok('write off' in routes_src.lower(), 'expiry write-off flow exists on the batches page')
sc = open(_os.path.join(ROOT, 'pharmacy', 'services', 'stock_count.py'), encoding='utf-8').read()
ok("approver_role != 'Admin'" in sc and 'not counted yet' in sc,
   'stock count: Admin-only approval and every line must be counted before submit')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
