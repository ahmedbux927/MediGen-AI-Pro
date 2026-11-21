"""Stage 4 (Master Prompt v4): held bills are wired end to end.

The held_bills service existed but no route or page used it. Now:
- POST /sales/hold parks the current bill (same form fields as a sale).
- GET /sales/held lists open holds; resume returns the bill to the sale page
  through the existing prefill path; discard closes it.
- Service behaviour is exercised with a fake cursor (no MySQL needed).
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


routes = read('pharmacy/routes/sales.py')
for endpoint in ('def hold_sale', 'def held_bills_page', 'def resume_held_bill', 'def discard_held_bill'):
    ok(endpoint in routes, f'route exists: {endpoint}')
ok("session['resume_hold']" in routes and "session.pop('resume_hold'" in routes,
   'resume flows through the session into the sale page prefill')
ok('prefill = [{\'mid\': l[\'medicine_id\']' in routes, 'resumed lines become sale prefill lines')

sale_tpl = read('templates/new_sale.html')
ok("formaction=\"{{ url_for('hold_sale') }}\"" in sale_tpl, 'sale page has a Hold bill button (formaction)')
ok("url_for('held_bills_page')" in sale_tpl, 'sale page links to Held bills')

held_tpl = read('templates/held_bills.html')
ok("url_for('resume_held_bill'" in held_tpl and "url_for('discard_held_bill'" in held_tpl,
   'held bills page has Resume and Discard actions')

# ---- service behaviour with a fake cursor ----
from pharmacy.services import held_bills as HB  # noqa: E402


class FakeCur:
    def __init__(self):
        self.row = None
        self.lastrowid = 7
        self.rowcount = 0

    def execute(self, sql, params=None):
        s = ' '.join(sql.split())
        if s.startswith('SELECT COUNT(*)'):
            self._one = {'n': 0}
        elif 'FOR UPDATE' in s:
            self._one = self.row
        elif s.startswith('SELECT status FROM held_bills'):
            self._one = {'status': self.row['status']} if self.row else None
        elif s.startswith('INSERT INTO held_bills'):
            import json
            self.row = {'hold_id': 7, 'status': 'open', 'payload': params[3]}
        elif s.startswith('UPDATE held_bills'):
            if "status='resumed'" in s:
                self.row['status'] = 'resumed'
            elif "status='discarded'" in s:
                self.row['status'] = 'discarded'
            self.rowcount = 1

    def fetchone(self):
        return self._one


cur = FakeCur()
hid = HB.hold_bill(cur, 1, 1, None, {5: 2, 9: 1}, 'wait karo')
ok(hid == 7 and cur.row['status'] == 'open', 'hold_bill saves an open hold')
payload = HB.resume_hold(cur, 7)
ok(payload['lines'] == [{'medicine_id': 5, 'quantity': 2}, {'medicine_id': 9, 'quantity': 1}],
   'resume_hold returns the saved lines')
try:
    HB.resume_hold(cur, 7)
    ok(False, 'a hold can be resumed only once')
except HB.HoldError:
    ok(True, 'a hold can be resumed only once')
try:
    HB.hold_bill(cur, 1, 1, None, {})
    ok(False, 'an empty bill cannot be held')
except HB.HoldError:
    ok(True, 'an empty bill cannot be held')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
