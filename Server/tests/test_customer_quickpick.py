"""v73: find a customer by phone while billing. Phone rules + wiring checks. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services.phone_search import normalise_phone as N, search_customers
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

ok(N('0300-1234567') == '3001234567', 'dashed local number matches the stored form')
ok(N('+92 300 1234567') == '3001234567', '+92 format matches')
ok(N('00923001234567') == '3001234567', '0092 format matches')
ok(N('3001234567') == '3001234567', 'bare 10 digits match')
ok(N('030') == '', 'fewer than 4 digits is not searched (would list too many)')
ok(N('') == '' and N('abc') == '', 'empty or text-only input is not searched')

class FakeCur:
    def __init__(self): self.calls = []
    def execute(self, sql, p=None): self.calls.append((sql, p))
    def fetchall(self): return [{'customer_id': 3, 'name': 'Ali', 'contact_number': '03001234567', 'last_sale': None, 'balance': 150}]
c = FakeCur()
rows = search_customers(c, '0300-123', 8)
ok(c.calls and c.calls[0][1] == ('%0300123%', 8) and rows[0]['name'] == 'Ali', 'search uses the normalised digits and the limit')
c = FakeCur()
ok(search_customers(c, '12', 8) == [] and c.calls == [], 'too-short search never touches the database')

route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'customer_search.py'), encoding='utf-8').read()
ok("@app.route('/customers/search')" in route and 'PS.search_customers' in route, 'search route exists and uses the phone service')
ok("'balance': float(r['balance'] or 0)" in route, 'balance is sent as a plain number')
ok("if 'user_id' not in session" in route, 'search needs a logged-in session')
ok('from . import customer_search' in open(_os.path.join(ROOT, 'pharmacy', 'routes', '__init__.py'), encoding='utf-8').read(), 'search route is registered')
tpl = open(_os.path.join(ROOT, 'templates', 'new_sale.html'), encoding='utf-8').read()
ok('id="custPhone"' in tpl and 'id="custResults"' in tpl, 'billing page has the phone box and results list')
ok("fetch('/customers/search?phone='" in tpl, 'phone box calls the search route')
ok('id="quickContact"' in tpl and "m.value = phone" in tpl, 'Add new customer opens with the typed number filled in')
ok("sel.value = String(c.customer_id)" in tpl, 'picking a result sets the customer dropdown')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
