"""Stage 5 (Master Prompt v4): catalog import follows ONE flow —
upload, parse, PREVIEW with errors marked, confirm, one transaction,
an import record is saved, and Undo reverses the batch when safe.

Checks the plan engine round-trip (plan -> JSON -> plan keeps actions),
the routes/templates wiring, and the migration. No MySQL needed.
"""
import datetime
import json
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


mig = read('database/migrations/014_import_preview.sql')
ok('import_previews' in mig and 'import_batches' in mig, 'migration 014 creates preview + batch tables')

routes = read('pharmacy/routes/products.py')
for endpoint in ('def import_preview', 'def import_preview_detail', 'def import_preview_confirm', 'def import_batch_undo'):
    ok(endpoint in routes, f'route exists: {endpoint}')
ok('PIMP.build_plan' in routes and 'PIMP.apply_plan' in routes, 'routes use the plan engine (build_plan/apply_plan)')
ok('updated_snapshot' in routes and 'created_ids' in routes, 'confirm records created ids and an update snapshot for undo')
ok('sale_items' in routes and 'purchase_items' in routes and 'Undo is blocked' in routes,
   'undo is blocked once an imported item is sold or purchased, with the reason shown')

ok("url_for('import_preview')" in read('templates/medicines.html'), 'medicines page links to Import with preview')
detail = read('templates/import_preview_detail.html')
ok('Confirm import' in detail and 'item.action' in detail and 'item.errors' in detail,
   'preview page shows per-row action and errors with a Confirm button')

# ---- engine round-trip: a plan survives JSON storage with its actions intact ----
from pharmacy.services import product_import as P  # noqa: E402

csv_text = ("name,barcode,selling_price,stock_quantity,batch_number,expiry_date\n"
            "Testmol 500mg,111222333,50,20,B-1,2027-05-01\n"
            "Bad Price Syrup,444555666,-5,10,B-2,2027-05-01\n"
            "Panadol,999888777,120,5,B-3,2027-05-01\n")
rows, _ = P.read_file(csv_text.encode('utf-8'), 'test.csv')
existing = {'barcodes': {'999888777': {'medicine_id': 1, 'name': 'Panadol', 'barcode': '999888777'}},
            'names': {P.name_key('Panadol'): {'medicine_id': 1, 'name': 'Panadol', 'barcode': '999888777'}}}
plan, summary = P.build_plan(rows, existing, datetime.date(2026, 11, 21))
acts = {i['name']: i['action'] for i in plan}
ok(acts.get('Testmol 500mg') == 'create', 'new row planned as create')
ok(acts.get('Bad Price Syrup') == 'error', 'negative price row planned as error (marked, not fixed)')
ok(acts.get('Panadol') == 'skip', 'existing row planned as skip by default')
restored = json.loads(json.dumps(plan, default=str))
ok([i['action'] for i in restored] == [i['action'] for i in plan],
   'plan survives JSON storage (preview) with actions intact')
plan2, _ = P.build_plan(rows, existing, datetime.date(2026, 11, 21), update_existing=True)
ok({i['name']: i['action'] for i in plan2}.get('Panadol') == 'update',
   'update_existing turns an existing row into an update')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
