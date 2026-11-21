"""v54 POS checkout service (scanner and mobile): barcode items, same rules as the counter. Mock DB only.
Run: python tests/test_pos_checkout.py
"""
import os, sys
from decimal import Decimal as D
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import pos
from pharmacy.services.sales import BillError

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

class DupEntry(Exception):
    def __init__(self):
        super().__init__(1062, "Duplicate entry")

class FakeDB:
    """Answers the SQL the checkout runs. Medicine 1 = Panadol at 100 (stock 50), barcode 8901234567890."""
    def __init__(self, dup=False):
        self.dup, self.log, self.last = dup, [], None
        self.medicines = {1: {'name': 'Panadol', 'price': D('100.00'), 'stock_quantity': 50, 'barcode': '8901234567890'},
                          2: {'name': 'Syrup', 'price': D('200.00'), 'stock_quantity': 5, 'barcode': '8900000000002'}}
    def cursor(self):
        return self
    def execute(self, sql, p=None):
        s = ' '.join(sql.split())
        self.log.append((s, p))
        self.last = None
        if s.startswith('SELECT * FROM cash_sessions WHERE closed_at IS NULL'):   # v87.03: drawer open
            self.last = [dict(session_id=1, opened_at=None, opening_amount=0, closed_at=None)]
            self.lastrowid = getattr(self, 'lastrowid', 0); return
        if s.startswith('INSERT INTO sale_guard') and self.dup:
            raise DupEntry()
        if 'FROM medicines WHERE barcode' in s:
            for mid, m in self.medicines.items():
                if m['barcode'] == p[0]:
                    self.last = [{'medicine_id': mid}]
            self.last = self.last or []
        elif s.startswith('SELECT name, price, stock_quantity FROM medicines'):
            m = self.medicines.get(p[0])
            self.last = [dict(name=m['name'], price=m['price'], stock_quantity=m['stock_quantity'])] if m else []
        elif 'COUNT(*) AS n FROM batches' in s:
            self.last = [{'n': 0}]
        elif 'FROM medicines WHERE medicine_id IN' in s:
            self.last = []
        self.lastrowid = 77 if s.startswith('INSERT INTO sales') else getattr(self, 'lastrowid', 0)
    def fetchone(self):
        if self.last is None:
            return None
        return self.last[0] if self.last else None
    def fetchall(self):
        return self.last or []
    def writes(self):
        return [s for s, _ in self.log if s.upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]

audits = []
def audit_fn(cur, action, entity=None, entity_id=None, details='', before=None, after=None, status='ok'):
    audits.append(action)

def run(body, role='Pharmacist', dup=False, db=None):
    db = db or FakeDB(dup=dup)
    return pos.checkout(db, 3, role, body, 0.0, 10, audit_fn), db

def raises(body, text, **kw):
    try:
        run(body, **kw)
        return False
    except BillError as e:
        return text in str(e)
    except Exception:
        return False

# --- happy path: scanner barcode
res, db = run({'items': [{'barcode': '8901234567890', 'quantity': 2}], 'payment_method': 'Cash'})
ok(res['sale_id'] == 77 and res['total'] == 200.0 and res['paid'] == 200.0 and res['balance'] == 0,
   'barcode scan: 2 x 100 = 200, paid in full, sale 77')
ok(any(s.startswith('UPDATE medicines') or s.startswith('INSERT INTO sale_items') for s in db.writes()),
   'barcode scan writes sale items')
ok(audits == ['sale.create'], 'one audit row: sale.create')

# --- medicine_id works too, and two lines add up
res, _ = run({'items': [{'medicine_id': 1, 'quantity': 1}, {'barcode': '8900000000002', 'quantity': 1}],
              'payment_method': 'Card'})
ok(res['total'] == 300.0, 'two lines (medicine_id and barcode) add up')

# --- discount and partial payment (udhaar with customer)
res, _ = run({'items': [{'medicine_id': 2, 'quantity': 1}], 'discount': '10', 'discount_type': 'percent',
              'paid': '100', 'customer_id': 5})
ok(res['total'] == 180.0 and res['balance'] == 80.0, 'percent discount then partial payment leaves balance')

# --- refusals
ok(raises({'items': [{'barcode': '0000000000000', 'quantity': 1}]}, 'is not in the medicine list'),
   'unknown barcode is refused with the code shown')
ok(raises({'items': []}, 'Add at least one item'), 'empty items refused')
ok(raises({'items': 'x'}, 'Add at least one item'), 'items not a list refused')
ok(raises({'items': [{'barcode': '8901234567890', 'quantity': 0}]}, 'more than zero'), 'quantity 0 refused')
ok(raises({'items': [{'barcode': '8901234567890', 'quantity': 'abc'}]}, 'whole number'), 'text quantity refused')
ok(raises({'items': [{'quantity': 1}]}, 'needs a barcode or a medicine_id'), 'item with no code refused')
ok(raises({'items': [{'medicine_id': 1, 'quantity': 999}]}, 'Insufficient stock'), 'more than stock refused')
ok(raises({'items': [{'medicine_id': 1}], 'payment_method': 'Bitcoin'}, 'Payment must be'), 'unknown payment refused')
ok(raises({'items': [{'medicine_id': 1}], 'discount': 'x'}, 'Discount must be a number'), 'bad discount refused')
ok(raises({'items': [{'medicine_id': 1}], 'paid': 'nan'}, 'Paid amount must be a number'), 'nan paid refused')
ok(raises({'items': [{'medicine_id': 1}], 'paid': '50'}, 'needs a customer'), 'udhaar without customer refused')
ok(raises({'items': [{'medicine_id': 1}], 'discount': '20', 'discount_type': 'percent'},
          'Cashier can give at most', role='Cashier'), 'cashier discount above cap refused')
ok(raises(['not', 'an', 'object'], 'Send a JSON object'), 'non-object body refused')

# --- same bill sent again: DuplicateBill, nothing saved
try:
    run({'items': [{'medicine_id': 1}]}, dup=True)
    ok(False, 'duplicate bill is refused')
except pos.DuplicateBill:
    ok(True, 'duplicate bill is refused (DuplicateBill, 409 in the route)')

# --- scheduled medicine needs a prescription
class Sched(FakeDB):
    def execute(self, sql, p=None):
        super().execute(sql, p)
        if 'FROM medicines WHERE medicine_id IN' in ' '.join(sql.split()):
            self.last = [{'medicine_id': 1, 'name': 'Panadol', 'schedule': 'Narcotic'}]
db = Sched()
ok(raises({'items': [{'medicine_id': 1}]}, 'Prescription needed', db=db), 'scheduled medicine without prescription refused')

print(f'\nTOTAL {PASS + FAIL}  PASS {PASS}  FAIL {FAIL}')
sys.exit(1 if FAIL else 0)
