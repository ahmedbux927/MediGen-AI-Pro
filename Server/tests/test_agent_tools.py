"""v54 AI agent tool layer: read tools never write; write actions need a one-time confirmation token. Mock DB only.
Run: python tests/test_agent_tools.py
"""
import os, sys, json, hashlib
from datetime import datetime, timedelta, date
from decimal import Decimal as D
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import agent_tools as T

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

NOW = datetime(2026, 10, 25, 9, 0, 0)

class FakeDB:
    def __init__(self):
        self.log, self.last, self.rowcount = [], None, 1
        self.agent_row = None           # what SELECT ... FROM agent_actions returns
        self.lastrowid = 0
    def cursor(self):
        return self
    def execute(self, sql, p=None):
        s = ' '.join(sql.split())
        self.log.append((s, p))
        self.last = []
        self.rowcount = 1
        if 'FROM agent_actions WHERE token_hash' in s:
            self.last = [self.agent_row] if self.agent_row else []
        elif s.startswith('UPDATE medicines'):
            self.rowcount = 1
        elif s.startswith('INSERT INTO customers'):
            self.lastrowid = 42
        elif 'COUNT(*) AS invoices' in s:
            self.last = [{'invoices': 18, 'revenue': D('48750.00')}]
        elif 'FROM medicines WHERE barcode' in s or 'LOWER(name) LIKE' in s:
            self.last = [{'medicine_id': 1, 'name': 'Panadol', 'stock_quantity': 12, 'price': D('100'),
                          'rack_location': 'A-3', 'schedule': None, 'barcode': None}]
        elif 'FROM medicines' in s and 'reorder_level' in s:
            self.last = [{'medicine_id': 1, 'name': 'Panadol', 'stock_quantity': 12, 'reorder_level': 20}]
    def fetchone(self):
        return self.last[0] if self.last else None
    def fetchall(self):
        return list(self.last or [])
    def writes(self):
        return [s for s, _ in self.log if s.upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]

audits = []
def audit_fn(cur, action, entity=None, entity_id=None, details='', before=None, after=None, status='ok'):
    audits.append((action, entity_id))

def raises(fn, text):
    try:
        fn(); return False
    except T.AgentError as e:
        return text in str(e)

# ---------------- READ tools: SELECT only
db = FakeDB()
found = T.find_medicine(db, 'pan')
ok(found and found[0]['name'] == 'Panadol', 'find_medicine by name')
T.find_medicine(db, '8901234567890')
T.low_stock(db)
T.expiring(db, date(2026, 10, 25), 30)
summary = T.today_summary(db, date(2026, 10, 25))
ok(summary['invoices'] == 18 and summary['revenue'] == 48750.0, 'today_summary returns counts and revenue')
ok(db.writes() == [], 'read tools run no INSERT, UPDATE or DELETE')
ok(T.find_medicine(FakeDB(), '   ') == [], 'empty search returns nothing')
low = T.low_stock(FakeDB())
ok(low and low[0]['severity'] in ('out', 'critical', 'low'), 'low_stock uses the inventory rules')

# ---------------- WRITE: propose
db = FakeDB()
p = T.propose(db, 3, 'set_shelf_location', {'medicine_id': '7', 'shelf_location': ' Rack B2 '}, NOW)
ok(p['token'].startswith('agt_') and len(p['token']) > 20, 'propose returns a confirmation token')
ok(p['summary'] == "Set shelf location of medicine #7 to 'Rack B2'", 'propose returns a readable summary')
ins = [(s, prm) for s, prm in db.log if s.startswith('INSERT INTO agent_actions')][0][1]
ok(ins[0] == hashlib.sha256(p['token'].encode()).hexdigest(), 'only the SHA-256 of the token is stored')
ok(p['token'] not in json.dumps(ins, default=str), 'the raw token is not stored anywhere')
ok(ins[5] == datetime(2026, 10, 25, 9, 5, 0), 'token expires after 5 minutes')
ok(any(s.startswith("UPDATE agent_actions SET status = 'cancelled'") for s, _ in db.log),
   'a new proposal cancels the user\'s older pending one')

ok(raises(lambda: T.propose(FakeDB(), 3, 'delete_all_medicines', {}, NOW), 'not allowed'), 'non-whitelisted action refused')
ok(raises(lambda: T.propose(FakeDB(), 3, 'set_shelf_location', {'medicine_id': 7}, NOW), 'Missing: shelf_location'),
   'missing field refused')
ok(raises(lambda: T.propose(FakeDB(), 3, 'set_shelf_location', {'medicine_id': 'x', 'shelf_location': 'A'}, NOW),
          'medicine_id must be a number'), 'non-number medicine_id refused')
ok(raises(lambda: T.propose(FakeDB(), 3, 'add_customer', 'text', NOW), 'Parameters must be an object'),
   'params not an object refused')
p2 = T.propose(FakeDB(), 3, 'add_customer', {'name': 'Ali', 'contact_number': '0300-1234567'}, NOW)
ok(p2['summary'] == "Add customer 'Ali' (0300-1234567)", 'add_customer summary includes the number')

# ---------------- WRITE: confirm
raw = p['token']
def row_for(user=3, status='pending', expires=NOW + timedelta(minutes=5), action='set_shelf_location', params=None):
    return {'action_id': 9, 'user_id': user, 'action': action, 'status': status, 'expires_at': expires,
            'params': json.dumps(params or {'medicine_id': 7, 'shelf_location': 'Rack B2'})}

db = FakeDB(); db.agent_row = row_for()
out = T.confirm(db, 3, raw, NOW, audit_fn)
ok(out['action'] == 'set_shelf_location' and out['result']['shelf_location'] == 'Rack B2',
   'confirm with the right user and token runs the change')
ok(any(s.startswith('UPDATE medicines SET rack_location') for s, _ in db.log), 'confirm updates the shelf location')
ok(audits == [('agent.shelf_location', 7)], 'confirm writes one audit row')
ok(any("SET status = 'done'" in s for s, _ in db.log), 'token is marked done in the same transaction')

db = FakeDB(); db.agent_row = row_for(user=4)
ok(raises(lambda: T.confirm(db, 3, raw, NOW, audit_fn), 'Invalid confirmation token'),
   'another user cannot use the token')
db = FakeDB(); db.agent_row = row_for(status='done')
ok(raises(lambda: T.confirm(db, 3, raw, NOW, audit_fn), 'already used'), 'a used token is refused (one time)')
db = FakeDB(); db.agent_row = row_for(expires=NOW - timedelta(seconds=1))
ok(raises(lambda: T.confirm(db, 3, raw, NOW, audit_fn), 'expired'), 'an expired token is refused')
db = FakeDB()
ok(raises(lambda: T.confirm(db, 3, 'agt_wrong', NOW, audit_fn), 'Invalid confirmation token'),
   'unknown token refused')
ok(raises(lambda: T.confirm(db, 3, 'hello', NOW, audit_fn), 'Invalid confirmation token'),
   'token without the agt_ prefix refused')

# executor failure: the error reaches the caller, who must roll back (the done mark goes with it)
db = FakeDB(); db.agent_row = row_for(); db.rowcount = 1
class Missing(FakeDB):
    def execute(self, sql, p=None):
        super().execute(sql, p)
        if s_is_update_medicine(sql):
            self.rowcount = 0
def s_is_update_medicine(sql):
    return ' '.join(sql.split()).startswith('UPDATE medicines')
db = Missing(); db.agent_row = row_for()
ok(raises(lambda: T.confirm(db, 3, raw, NOW, audit_fn), 'Medicine not found'),
   'missing medicine stops the change (caller rolls back)')

db = FakeDB(); db.agent_row = row_for(action='add_customer', params={'name': 'Ali', 'contact_number': None})
res = T.confirm(db, 3, raw, NOW, audit_fn)
ok(res['result'] == {'customer_id': 42}, 'confirm add_customer creates the customer')

print(f'\nTOTAL {PASS + FAIL}  PASS {PASS}  FAIL {FAIL}')
sys.exit(1 if FAIL else 0)
