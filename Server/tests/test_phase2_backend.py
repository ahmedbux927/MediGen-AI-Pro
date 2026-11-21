"""Phase 2 backend: phone search, hold and resume bills. Pure + mock cursor. No MySQL needed.
Run: python tests/test_phase2_backend.py
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import phone_search as PS
from pharmacy.services import held_bills as HB
from pharmacy.services import migrations as M

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

for typed in ['03001234567', '0300-1234567', '+92 300 1234567', '00923001234567', '3001234567', '(0300) 123 4567']:
    ok(PS.normalise_phone(typed) == '3001234567', f'phone "{typed}" matches 3001234567')
ok(PS.normalise_phone('0300') == '0300', 'four digits is enough to search')
ok(PS.normalise_phone('03') == '', 'two digits is too short to search (empty result)')
ok(PS.normalise_phone('') == '' and PS.normalise_phone('abc') == '', 'no digits, nothing to search')

class SearchCur:
    def __init__(self): self.args = None
    def execute(self, sql, p=None): self.args = p
    def fetchall(self): return [{'customer_id': 1}]
c = SearchCur(); ok(PS.search_customers(c, '0300123', 10) == [{'customer_id': 1}] and c.args == ('%0300123%', 10), 'partial search keeps the typed digits and caps the limit')
c = SearchCur(); PS.search_customers(c, '0300', 999); ok(c.args[1] == 50, 'limit is capped at 50')
c = SearchCur(); ok(PS.search_customers(c, '03', 10) == [] and c.args is None, 'short search runs no query')

class Cur:
    """In-memory held_bills table for the tests."""
    def __init__(self, rows=None, open_count=0):
        self.rows = rows if rows is not None else {}
        self.open_count, self.next_id, self._last, self.rowcount = open_count, 1, '', 0
        self.lastrowid = None
    def execute(self, sql, p=None):
        self._last = ' '.join(sql.split()); self._p = p
        if self._last.startswith('INSERT INTO held_bills'):
            self.lastrowid = self.next_id; self.rows[self.next_id] = {'hold_id': self.next_id, 'status': 'open',
                                                                     'payload': p[3], 'counter_no': p[0]}
            self.next_id += 1
        if self._last.startswith('UPDATE held_bills SET status=') and self._p and 'hold_id' in self._last or \
           (self._last.startswith("UPDATE held_bills SET status='") and self._p):
            hid = self._p[0]
            self.rows[hid]['status'] = 'resumed' if "'resumed'" in self._last else 'discarded'
    def fetchone(self):
        if 'COUNT(*)' in self._last:
            return {'n': self.open_count + sum(1 for r in self.rows.values() if r['status'] == 'open')}
        if self._last.startswith('SELECT hold_id, status, payload') or self._last.startswith('SELECT status FROM held_bills'):
            return self.rows.get(self._p[0])
        return None
    def fetchall(self): return []

cur = Cur()
hid = HB.hold_bill(cur, 1, 2, 9, {5: 2, 3: 1}, 'call back')
data = json.loads(cur.rows[hid]['payload'])
ok(hid == 1 and data['lines'] == [{'medicine_id': 3, 'quantity': 1}, {'medicine_id': 5, 'quantity': 2}] and data['customer_id'] == 9,
   'hold saves the lines (sorted) and the customer')
ok(data['note'] == 'call back', 'hold keeps the note')
try:
    HB.hold_bill(Cur(), 1, 2, None, {}); ok(False, 'an empty bill cannot be held')
except HB.HoldError:
    ok(True, 'an empty bill cannot be held')
try:
    HB.hold_bill(Cur(open_count=10), 1, 2, None, {1: 1}); ok(False, 'the 11th open hold on a counter is refused')
except HB.HoldError as e:
    ok('already has 10' in str(e), 'the 11th open hold on a counter is refused')
try:
    HB.hold_bill(Cur(), 1, 21, None, {1: 1}); ok(False, 'counter 21 is refused')
except HB.HoldError:
    ok(True, 'counter 21 is refused')
cur = Cur(rows={1: {'hold_id': 1, 'status': 'open', 'payload': json.dumps({'customer_id': None, 'lines': [], 'note': ''})}})
back = HB.resume_hold(cur, 1)
ok(back == {'customer_id': None, 'lines': [], 'note': ''} and cur.rows[1]['status'] == 'resumed', 'resume returns the bill and marks it resumed')
try:
    HB.resume_hold(cur, 1); ok(False, 'a hold cannot be resumed twice')
except HB.HoldError as e:
    ok('already resumed' in str(e), 'a hold cannot be resumed twice')
try:
    HB.resume_hold(Cur(), 99); ok(False, 'unknown hold is refused')
except HB.HoldError:
    ok(True, 'unknown hold is refused')
cur = Cur(rows={2: {'hold_id': 2, 'status': 'open', 'payload': '{}'}})
HB.discard_hold(cur, 2)
ok(cur.rows[2]['status'] == 'discarded', 'discard marks the hold discarded')

ok(any(n == 'held_bills' for _, n, _ in M.load_migrations()), 'migration 004 (held bills) is in the project')
print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
