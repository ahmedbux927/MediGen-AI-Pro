"""B1 regression: a sale with a drip/injection line must not run DDL (CREATE/ALTER) inside the sale.
MySQL DDL commits the open transaction, so an error later would leave a half-saved sale. No MySQL needed."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import drip_record as DR
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))


class FakeCursor:
    def __init__(self, med_rows):
        self.med_rows = med_rows
        self.statements = []
        self._last = None
    def execute(self, sql, params=None):
        self.statements.append(sql.strip().split()[0].upper())
        self._last = sql
    def fetchall(self):
        return list(self.med_rows) if 'FROM medicines' in (self._last or '') else []
    def fetchone(self):
        return None


meds = [
    {'medicine_id': 1, 'dosage_form': 'Tablet', 'strength': '500 mg'},
    {'medicine_id': 2, 'dosage_form': 'Injection', 'strength': '1 g'},
]
DR._table_ready = False          # the state that used to trigger CREATE TABLE in the middle of a sale
cur = FakeCursor(meds)
lines = [(1, 10.0, [(11, 2)]), (2, 50.0, [(12, 1)])]     # one tablet + one injection in one sale
n = DR.auto_record_sale(cur, 77, 5, 3, lines, {2: 'IM injection'})

ok(n == 1, 'one drip record written for the injection line only')
ok('CREATE' not in cur.statements and 'ALTER' not in cur.statements,
   'no CREATE or ALTER inside the sale (B1: DDL commits the sale early)')
ok(cur.statements.count('INSERT') == 1, 'exactly one INSERT for the drip line')

print('\n'.join(('PASS ' if c else 'FAIL ') + m for m, c in RESULTS))
