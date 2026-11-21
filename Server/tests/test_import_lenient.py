"""v86.43: import is lenient: bad rows are skipped with a warning, good rows load, and photo lines become a CSV.
Run through tests/run_all.py, or directly: python tests/test_import_lenient.py"""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
from pharmacy.services import product_sections as PS

items, errs, warns = PS.parse_products_report(b'Medicine;Qty\nAmoxicillin;10 pcs\n;5\nCalpol;abc\n', 'syrups')
ok(not errs and [i['name'] for i in items] == ['Amoxicillin', 'Calpol'], 'semicolon file: good rows load, empty-name row is skipped')
ok(items[0]['qty'] == 10 and items[1]['qty'] == 0, '"10 pcs" reads as 10; a non-number quantity becomes 0')
ok(any('name is empty' in w for w in warns) and any('not a number' in w for w in warns), 'skipped rows are reported as warnings with line numbers')
items, errs, _ = PS.parse_products_report(b'name,strength\nCalpol,0\nBrufin,500 mg\n', 'syrups')
ok(items[0]['strength'] is None and items[1]['strength'] == '500 mg', 'junk strength "0" is ignored; real strength is kept')
items, errs, _ = PS.parse_products_report(b'name\n1. Calpol Syrup Rs. 120\n2) Brufin\n', 'syrups')
ok([i['generic_name'] for i in items] == ['Calpol Syrup', 'Brufin'], 'list numbers and "Rs. 120" tails are removed from names')
_, errs, _ = PS.parse_products_report(b'price,stock\n,\n', 'syrups')
ok(errs and 'name column' in errs[0], 'no names at all: one clear message, in plain words')
_, errs, _ = PS.parse_products_report(b'', 'syrups')
ok(errs, 'empty file gives a message, not a crash')
csv_bytes, kept = PS.photo_lines_to_csv(['1. Calpol Syrup 120mg Rs. 120', 'Sr Name Price', 'Brufin Syrup', 'x', '12'])
ok(kept == 2 and csv_bytes.startswith(b'name'), 'photo lines: table headers, numbers and tiny lines are dropped')
items, errs, _ = PS.parse_products_report(csv_bytes, 'syrups')
ok(not errs and len(items) == 2, 'photo lines turned into CSV load through the same parser')

if __name__ == '__main__':
    fails = [m for m, good in RESULTS if not good]
    for m, good in RESULTS:
        print(('PASS ' if good else 'FAIL ') + m)
    print(f"\nTOTAL: {len(RESULTS)-len(fails)} passed, {len(fails)} failed")
