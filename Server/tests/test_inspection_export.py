"""Inspection report merge rules (no MySQL): sections, order, out-of-range flag, quantities."""
import os as _os, sys
from datetime import datetime
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import inspection_export as IE
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

controlled = [{'created_at': datetime(2026, 11, 10, 9, 30), 'medicine_name': 'Tramadol 50mg', 'schedule': 'H',
               'batch_number': 'B1', 'quantity': 10, 'customer_name': 'Walk-in', 'username': 'cashier1',
               'sale_id': 77}]
cold = [{'recorded_at': datetime(2026, 11, 9, 8, 0), 'location': 'Fridge 1', 'temperature_c': 4.2,
         'in_range': 1, 'note': None, 'username': 'owner'},
        {'recorded_at': datetime(2026, 11, 12, 8, 0), 'location': 'Fridge 1', 'temperature_c': 9.5,
         'in_range': 0, 'note': 'door left open', 'username': 'owner'}]
writeoffs = [{'created_at': datetime(2026, 11, 11, 12, 0), 'medicine_name': 'Cough syrup', 'change_qty': -24,
              'note': 'Write-off batch S9', 'username': 'admin'}]

table = IE.merge(controlled, cold, writeoffs)
ok(len(table) == 4, 'four rows: one controlled, two cold chain, one write-off')
ok([r[0] for r in table] == ['2026-11-09 08:00', '2026-11-10 09:30', '2026-11-11 12:00', '2026-11-12 08:00'],
   'rows are sorted oldest first across all sections')
ok(table[0][1] == 'Cold chain' and table[0][8] == 'In range', 'an in-range reading says In range')
ok(table[3][8].startswith('OUT OF RANGE') and 'door left open' in table[3][8], 'an out-of-range reading is flagged with its note')
ok(table[1][1] == 'Controlled drug' and table[1][2] == 'Tramadol 50mg' and table[1][4] == '10', 'controlled row keeps item and quantity')
ok(table[1][8] == 'Sale #77', 'controlled row links to the sale')
ok(table[2][4] == '-24' and table[2][8] == 'Removed (expired)', 'write-off shows the negative change and status')
ok(all(len(r) == len(IE.HEADERS) for r in table), 'every row has the same number of columns as the headers')
ok(IE.merge([], [], []) == [], 'empty input gives an empty report')
ok(IE.merge(None, None, None) == [], 'None input is treated as empty')

print('\n'.join(('PASS ' if c else 'FAIL ') + m for m, c in RESULTS))
