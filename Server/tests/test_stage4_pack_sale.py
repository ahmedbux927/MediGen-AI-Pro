"""Stage 4 (Master Prompt v4): sell by pack as well as by unit.

- Migration 013 adds medicines.units_per_pack (runs once, at startup).
- Product edit saves it with validation.
- The counter screen carries data-pack on each item and converts
  "2pk*..." into units in both add paths (picker and scan box).
Stock and prices stay per unit; only the typed quantity is converted.
"""
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


mig = read('database/migrations/013_units_per_pack.sql')
ok('ADD COLUMN units_per_pack' in mig and 'ALTER TABLE medicines' in mig,
   'migration 013 adds units_per_pack to medicines')

prod = read('pharmacy/routes/products.py')
ok("request.form.get('units_per_pack')" in prod and 'units_per_pack=%s' in prod,
   'product edit reads and saves units_per_pack')
ok('1 <= int(upp_raw) <= 10000' in prod, 'units_per_pack is range-validated (1..10000)')

edit_tpl = read('templates/products_edit.html')
ok('name="units_per_pack"' in edit_tpl, 'product edit form has the Units per pack field')

sales = read('pharmacy/routes/sales.py')
ok('m.units_per_pack' in sales, 'sale page query loads units_per_pack')

tpl = read('templates/new_sale.html')
ok('data-pack="{{ m.units_per_pack or \'\' }}"' in tpl, 'each sale item option carries data-pack')
ok('(pk)?' in tpl and 'pack: pack' in tpl, 'parseQuery understands the pk* pack syntax')
ok(tpl.count('p.mult = p.mult * pu') + tpl.count('mult = mult * pu') >= 2,
   'both add paths (picker and scan box) convert packs to units')
ok('has no pack size set' in tpl and 'No pack size is set' in tpl,
   'items without a pack size get a clear English message, not a wrong quantity')
ok('2pk*barcode' in tpl, 'the keys hint on the sale page documents pack entry')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
