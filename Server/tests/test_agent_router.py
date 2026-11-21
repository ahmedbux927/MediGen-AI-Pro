"""v72: chat -> agent write proposals (parser + wiring). No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services.agent_router import parse_write as P
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

r = P('shelf Panadol to A-3')
ok(r and r['action'] == 'set_shelf_location' and r['medicine_name'] == 'Panadol' and r['params'] == {'shelf_location': 'A-3'}, 'shelf X to Y is a shelf proposal')
r = P('Panadol ka shelf A-3')
ok(r and r['medicine_name'] == 'Panadol' and r['params']['shelf_location'] == 'A-3', 'Roman Urdu "X ka shelf Y" works')
r = P('Panadol shelf = B-12')
ok(r and r['params']['shelf_location'] == 'B-12', 'shelf with = works')
r = P('shelf to A-3')
ok(r is None, 'shelf without a medicine name is not treated as a write (normal chat answers)')
r = P('add customer Ali Khan 0300-1234567')
ok(r and r['action'] == 'add_customer' and r['params'] == {'name': 'Ali Khan', 'contact_number': '03001234567'}, 'add customer with phone: phone is cleaned')
r = P('naya customer Sara')
ok(r and r['params'] == {'name': 'Sara'}, 'naya customer without phone')
r = P('add customer 0300')
ok(r and r['params'] == {'name': '0300'} or (r and 'error' in r) or r is None, 'short numbers do not become phone numbers')
ok(P('add customer') is None, 'add customer with no name is left to the normal chat')
ok(P('low stock') is None and P('Panadol') is None and P('') is None, 'read questions and empty text are not writes')
ok(P('x' * 10 + ' shelf ' + 'y' * 60) is None or P('x' * 10 + ' shelf ' + 'y' * 60)['params']['shelf_location'] is not None, 'long shelf text does not crash the parser')

src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'chatbot.py'), encoding='utf-8').read()
ok('AR.parse_write(question)' in src and '_agent_chat(question, parsed)' in src, 'chat API sends write commands to the agent before the chat engine')
ok("AGENT_ROLES = ('Admin', 'Pharmacist')" in src, 'only Admin and Pharmacist can propose changes')
agent = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'agent.py'), encoding='utf-8').read()
ok("@app.route('/agent/confirm', methods=['POST'])" in agent, 'confirm route exists')
ok('AT.confirm(cur, session[' in agent and 'mysql.connection.rollback()' in agent, 'confirm runs the saved token and rolls back on error')
ok("if session.get('role') not in ('Admin', 'Pharmacist')" in agent, 'confirm checks the role again')
ok('from . import agent' in open(_os.path.join(ROOT, 'pharmacy', 'routes', '__init__.py'), encoding='utf-8').read(), 'agent routes are registered')
tpl = open(_os.path.join(ROOT, 'templates', 'chatbot.html'), encoding='utf-8').read()
ok("if (d.token) addConfirm(d.token)" in tpl and "url_for('agent_confirm')" in tpl, 'chat page shows Confirm for a proposal')
ok('agent-cancel' in tpl, 'chat page has Cancel too')
tools = open(_os.path.join(ROOT, 'pharmacy', 'services', 'agent_tools.py'), encoding='utf-8').read()
ok('CREATE TABLE IF NOT EXISTS agent_actions' in tools, 'agent_actions table is created at runtime too')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
