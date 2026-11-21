"""v83: stock triggers are checked at startup and never added twice. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import stock_triggers as ST
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

names = sorted(n for n, _, _ in ST.missing([]))
ok(names == ['trg_purchase_stock', 'trg_sale_stock'], 'with no triggers, both stock triggers are created')
ok(ST.missing([('trg_sale_stock', 'sale_items'), ('trg_purchase_stock', 'purchase_items')]) == [], 'when both exist nothing is created again')
ok([n for n, _, _ in ST.missing([('my_old_sale_rule', 'sale_items')])] == ['trg_purchase_stock'],
   'a sale trigger under another name is still counted, so no second one is added (no double stock change)')
ok([n for n, _, _ in ST.missing([('trg_sale_stock', 'sale_items')])] == ['trg_purchase_stock'], 'only the missing purchase trigger is created')
sale_ddl = ST.SALE_TRIGGER[2]
ok('stock_quantity = stock_quantity - NEW.quantity' in sale_ddl and 'quantity = quantity - NEW.quantity' in sale_ddl,
   'sale trigger lowers both medicine stock and batch stock')
ok('stock_quantity = stock_quantity + NEW.quantity' in ST.PURCHASE_TRIGGER[2], 'purchase trigger raises medicine stock')
ok(sale_ddl.startswith('CREATE TRIGGER trg_sale_stock AFTER INSERT ON sale_items'), 'sale trigger is on sale_items after insert')

schema = open(_os.path.join(ROOT, 'database', 'schema.sql'), encoding='utf-8').read()
ok('NEW.quantity' in schema and 'trg_sale_stock' in schema, 'the same sale trigger is in the schema file')
core = open(_os.path.join(ROOT, 'pharmacy', 'core.py'), encoding='utf-8').read()
ok('ensure_stock_triggers()          # v83' in core, 'startup creates missing stock triggers')
ok('stock triggers missing and could not be created' in core, 'a failure is logged as an error, not hidden')
live = open(_os.path.join(ROOT, 'tests', 'test_live_mysql.py'), encoding='utf-8').read()
ok("TRIGGER_NAME = 'trg_sale_stock'" in live and 'db.commit()   # end the old read snapshot' in live,
   'the live test checks the trigger exists and reads fresh stock after the sale')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
