"""v74: read-only agent queries (shelf location, phone lookup) in chat. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import agent_router as AR
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

ok(AR.parse_read('shelf Panadol') == {'read': 'medicine_shelf', 'text': 'Panadol'}, 'shelf X is a shelf question')
ok(AR.parse_read('Panadol ka shelf')['text'] == 'Panadol', 'X ka shelf works (Roman Urdu)')
ok(AR.parse_read('where is Panadol?')['text'] == 'Panadol', 'where is X works')
ok(AR.parse_read('kahan hai Brufen')['text'] == 'Brufen', 'kahan hai X works')
ok(AR.parse_read('0300-1234567') == {'read': 'customer_phone', 'text': '0300-1234567'}, 'a phone number looks up a customer')
ok(AR.parse_read('customer 03001234567')['read'] == 'customer_phone', 'customer <phone> works')
ok(AR.parse_read('123') is None, 'a short number is not a phone lookup')
ok(AR.parse_read('shelf Panadol to A-3') is None, 'shelf X to Y is a write (not a read)')
ok(AR.parse_read('add customer 0300') is None, 'add customer is never a read')
ok(AR.parse_read('low stock') is None and AR.parse_read('Panadol stock') is None, 'engine questions (low stock, stock) are left to the chat engine')
ok(AR.parse_read('') is None and AR.parse_read(None) is None, 'empty input is not a read')

ok(AR.shelf_answer([], 'Xyz').startswith('No medicine found'), 'no medicine found gives a clear message')
one = AR.shelf_answer([{'name': 'Panadol', 'rack_location': 'A-3', 'stock_quantity': 30, 'price': 10}], 'Panadol')
ok('shelf A-3' in one and 'stock 30' in one and 'Rs. 10' in one, 'one medicine shows shelf, stock and price')
nos = AR.shelf_answer([{'name': 'Brufen', 'rack_location': None, 'stock_quantity': 0, 'price': 20}], 'Brufen')
ok('shelf not set' in nos, 'missing shelf is shown as not set')
many = AR.shelf_answer([{'name': f'Med{i}', 'rack_location': 'B', 'stock_quantity': 1, 'price': 1} for i in range(12)], 'Med')
ok('12 medicines found' in many and many.count('• ') == 10, 'long list is capped at 10 lines')
ok(AR.customer_answer([], "0300")[:20].startswith('No customer found'), 'no customer for a number gives a clear message')
cust = AR.customer_answer([{'name': 'Ali', 'contact_number': '03001234567', 'balance': 150}], '0300')
ok('Ali' in cust and 'owes Rs. 150' in cust, 'customer line shows the udhaar balance')
ok('owes' not in AR.customer_answer([{'name': 'Sara', 'contact_number': None, 'balance': 0}], '0300'), 'no balance means no "owes" text')

route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'chatbot.py'), encoding='utf-8').read()
ok('read = AR.parse_read(question)' in route and '_agent_read(question, read)' in route, 'chat API routes read queries to the agent')
ok(route.index('AR.parse_write(question)') < route.index('AR.parse_read(question)'), 'write check runs before read check (writes never become reads)')
ok("AT.find_medicine(cur, read['text'], 10)" in route and "AT.find_customer(cur, read['text'], 8)" in route, 'read answers use the agent tools (read-only SELECT)')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
