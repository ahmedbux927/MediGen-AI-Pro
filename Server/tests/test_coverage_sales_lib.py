"""Coverage suite for pharmacy/routes/sales.py and pharmacy/lib.py. Mock database, no MySQL needed.
Run through tests/run_all.py, or directly: python tests/test_coverage_sales_lib.py"""
import os as _os, sys, types
from decimal import Decimal as D
from datetime import date, datetime
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc

# ---- configurable fake database -------------------------------------------------
STATE, LOG = {}, []
def reset(**kw):
    STATE.clear(); LOG.clear()
    STATE.update(meds={}, batches={}, sale=None, items=[], inv_items=[], payments=[], rx=None, rx_items=[],
                 rx_used=0, history=None, customers=[], settings=[], sales_rows=[], total=45, stats=None,
                 daily=[], period_items=[], low=[], expiry=[], pick=[], stock_after=50, lastrowid=100,
                 raise_on=None, dues=(D('0'), 0), guard_hit=False)
    STATE.update(kw)

def _route(sql, p):
    """Return (one, all) for a normalised SQL string and its parameters."""
    s, p = sql, (p or ())
    if 'information_schema' in s: return {'n': 1}, []
    # v87.03: a drawer is open in these tests (normal shop day), so cash bills are allowed
    if s.startswith('SELECT * FROM cash_sessions WHERE closed_at IS NULL'):
        return {'session_id': 1, 'opened_at': None, 'opening_amount': 0, 'closed_at': None}, []
    if s.startswith('SELECT name, price, stock_quantity FROM medicines'): return STATE['meds'].get(str(p[0])), []
    if s.startswith('SELECT COUNT(*) AS n FROM batches WHERE medicine_id'):
        return {'n': len(STATE['batches'].get(str(p[0]), []))}, []
    if 'FROM batches WHERE medicine_id' in s and 'FOR UPDATE' in s: return None, STATE['batches'].get(str(p[0]), [])
    if s.startswith('SELECT prescription_id, customer_id') : return STATE['rx'], []
    if s.startswith('SELECT pi.medicine_id'): return None, STATE['rx_items']
    if s.startswith('SELECT COUNT(*) AS n FROM sales WHERE prescription_id'): return {'n': STATE['rx_used']}, []
    if s.startswith('SELECT medical_history FROM customers'): return STATE['history'], []
    if s.startswith('SELECT total_amount, returned_amount, paid_amount FROM sales'):
        if STATE['raise_on'] and STATE['raise_on'] in s: raise RuntimeError('db down')
        return STATE['sale'], []
    if s.startswith('SELECT s.*, c.name AS customer_name FROM sales s'): return STATE['sale'], []
    if s.startswith('SELECT s.*, c.name AS customer_name, c.contact_number'): return STATE['sale'], []
    if s.startswith('SELECT s.*, c.name AS customer_name, u.full_name AS cashier FROM sales'): return STATE['sale'], []
    if s.startswith('SELECT s.*, c.name AS customer_name, u.full_name AS cashier, (') and 'LIMIT' in s:
        return None, STATE['sales_rows']
    if s.startswith('SELECT COUNT(*) AS total FROM sales'): return {'total': STATE['total']}, []
    if s.startswith('SELECT COUNT(*) AS cnt'): return STATE['stats'] or {'cnt': 3, 'revenue': D('4500')}, []
    if s.startswith('SELECT IFNULL(SUM(total_amount - returned_amount - paid_amount)'):
        return {'dues': STATE['dues'][0], 'due_count': STATE['dues'][1]}, []
    if s.startswith('SELECT stock_quantity FROM medicines'): return {'stock_quantity': STATE['stock_after']}, []
    if s.startswith('SELECT si.sale_item_id'): return None, STATE['items']
    if s.startswith('SELECT m.name AS medicine_name, SUM(si.quantity)'): return None, STATE['inv_items']
    if s.startswith('SELECT amount, method, created_at FROM sale_payments'): return None, STATE['payments']
    if s.startswith('SELECT m.medicine_id, m.name, m.barcode'): return None, STATE['pick']
    if s.startswith('SELECT c.customer_id, c.name'): return None, STATE['customers']
    if s.startswith('SELECT DATE(sale_date) AS sale_day'): return None, STATE['daily']
    if s.startswith('SELECT m.name, si.quantity'): return None, STATE['period_items']
    if s.startswith('SELECT name, stock_quantity, reorder_level'): return None, STATE['low']
    if s.startswith('SELECT m.name, b.batch_number'): return None, STATE['expiry']
    if s.startswith('SELECT setting_key, setting_value FROM app_settings'): return None, STATE['settings']
    return None, []

class DupEntry(Exception):
    pass

class Cur:
    def execute(self, sql, p=None):
        self.sql = ' '.join(sql.split()); self.p = p
        LOG.append((self.sql, p))
        if STATE.get('raise_on') and STATE['raise_on'] in self.sql and not self.sql.startswith('SELECT'):
            raise RuntimeError('db down')
        if STATE.get('guard_hit') and self.sql.startswith('INSERT INTO sale_guard'):
            raise DupEntry(1062, "Duplicate entry for key 'PRIMARY'")
        self._one, self._all = _route(self.sql, p)
    @property
    def lastrowid(self): return STATE['lastrowid']
    def fetchone(self): return self._one
    def fetchall(self): return list(self._all)
    def close(self): pass

class Conn:
    rollbacks = 0
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): Conn.rollbacks += 1

m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = Conn()
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m
import app as A
import pharmacy.routes  # noqa: F401  (registers every route)
from pharmacy.lib import _valid_date, _num, _like, _return_items, _as_date, get_all_settings, get_tax_rate, \
    get_cashier_max, get_setting, inject_shop, _report_dates, _sales_figures, _stock_rows, _expiry_rows, \
    _csv_response, flash_unexpected, _audit_json, audit, audit_direct, allergy_warnings, doctor_label, _clean_doctor
from flask import session as flask_session

RESULTS = []
def ok(cond, label):
    RESULTS.append((label, bool(cond)))
    print(('PASS ' if cond else 'FAIL ') + label)

def check(label, fn):
    """Run one check; an exception counts as a failure instead of stopping the suite."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        ok(False, f"{label} (raised {type(e).__name__}: {e})")

def login(role='Admin'):
    c = A.app.test_client(); c.get('/login')
    with c.session_transaction() as s:
        s.update(user_id=1, user_name='Ahmed', role=role); s['_csrf'] = 't'
    return c

F = {'csrf_token': 't'}
def flashes(c):
    with c.session_transaction() as s:
        return [msg for _, msg in s.get('_flashes', [])]
def inserts(prefix):
    return [p for sql, p in LOG if sql.startswith(prefix)]

MEDS = {'1': dict(name='Panadol', price=D('100.00'), stock_quantity=60),
        '2': dict(name='Brufen', price=D('50.00'), stock_quantity=30),
        '3': dict(name='OldMed', price=D('10.00'), stock_quantity=5),
        '4': dict(name='Amoxicillin', price=D('20.00'), stock_quantity=10)}
BATCHES = {'1': [dict(batch_id=11, quantity=20), dict(batch_id=12, quantity=40)],
           '2': [dict(batch_id=21, quantity=5)]}
SALE = dict(sale_id=1, total_amount=D('1000.00'), subtotal_amount=D('1000.00'), returned_amount=D('0.00'),
            paid_amount=D('1000.00'), customer_id=None, customer_name='Ali', contact_number='0300',
            email=None, medical_history=None, cashier='Ahmed', payment_method='Cash', due_amount=D('0'),
            discount_amount=D('0'), tax_amount=D('0'), tax_rate=D('0'), sale_date=datetime(2026, 10, 12, 10, 0),
            prescription_id=None, user_id=1)
RET_ITEMS = [dict(sale_item_id=5, medicine_id=1, batch_id=11, quantity=3, unit_price=D('100.00'),
                  name='Panadol', returned_qty=0)]
PERIOD = [dict(name='Panadol', quantity=3, unit_price=D('100'), returned_qty=0, unit_cost=D('60')),
          dict(name='Brufen', quantity=2, unit_price=D('50'), returned_qty=2, unit_cost=D('20')),  # fully returned: skipped
          dict(name='Panadol', quantity=1, unit_price=D('100'), returned_qty=0, unit_cost=D('60'))]
DAILY = [dict(sale_day=date(2026, 10, 12), invoices=2, revenue=D('300')),
         dict(sale_day=date(2026, 10, 11), invoices=1, revenue=D('100'))]

def fresh(**kw):
    reset(meds=dict(MEDS), batches=dict(BATCHES), **kw)
    Conn.rollbacks = 0
    return login('Admin')

def sale_post(c, **kw):
    d = {**F, 'payment_method': 'Cash', 'medicine_id[]': ['1'], 'quantity[]': ['30']}
    d.update(kw)
    LOG.clear()
    return c.post('/sales/new', data=d)

# ---- sales list ------------------------------------------------------------------
def t_list():
    reset(sales_rows=[dict(sale_id=7, sale_date=datetime(2026, 10, 12, 10, 0), customer_name='Ali', cashier='Ahmed',
                           total_amount=D('1000'), paid_amount=D('200'), returned_amount=D('100'),
                           payment_method='Cash', due_amount=D('700'))])
    c = login('Admin')
    r = c.get('/sales')
    ok(r.status_code == 200 and 'Ali' in r.get_data(as_text=True), 'sales list shows the stored sales')
    for q in ['?filter=due&q=Ali&from=2026-10-01&to=2026-10-31&page=2', '?filter=paid', '?filter=returned',
              '?from=31-12-2026&to=bad', '?q=12']:
        ok(c.get('/sales' + q).status_code == 200, f'sales list filter {q} renders')
check('sales list', t_list)

# ---- new sale (GET + POST) -------------------------------------------------------
def t_new_sale_get():
    c = fresh(pick=[dict(medicine_id=1, name='Panadol', barcode=None, price=D('100'), stock_quantity=60, fresh_qty=D(60), batch_count=2)],
              customers=[dict(customer_id=1, name='Ali', due=D('0'))])
    r = c.get('/sales/new')
    ok(r.status_code == 200 and 'Panadol' in r.get_data(as_text=True), 'new sale page lists medicines')
check('new sale GET', t_new_sale_get)

def t_sale_fifo():
    c = fresh(sale=None)
    r = sale_post(c)
    items = inserts('INSERT INTO sale_items')
    ok(r.status_code == 302 and '/invoice/100' in r.headers['Location'], 'sale saved and opens the receipt')
    ok(len(items) == 2 and items[0][2] == 11 and items[0][3] == 20 and items[1][2] == 12 and items[1][3] == 10,
       'quantity split FIFO: 20 from oldest batch, 10 from next')
    ok(inserts('INSERT INTO sale_payments'), 'a payment row is written when paid > 0')
    ok(any(sql.startswith('INSERT INTO audit_log') for sql, _ in LOG), 'sale writes an audit row')
check('sale FIFO', t_sale_fifo)

def t_double_submit():
    # B1: the same bill sent twice. The second one hits the guard row and is refused, nothing is saved.
    c = fresh(guard_hit=True)
    r = sale_post(c)
    ok(r.status_code == 302 and '/sales' in r.headers['Location'], 'double submit: redirected to the sales list')
    ok(not inserts('INSERT INTO sales'), 'double submit: no second sale row written')
    ok(not inserts('INSERT INTO sale_items') and not inserts('INSERT INTO sale_payments'),
       'double submit: no items or payments written')
    ok(any('just saved' in m for m in flashes(c)), 'double submit: the user is told the bill was just saved')
    ok(Conn.rollbacks >= 1, 'double submit: the transaction is rolled back (stock locks released)')
    c = fresh()
    sale_post(c)
    guard = inserts('INSERT INTO sale_guard')
    ok(len(guard) == 1 and len(guard[0][0]) == 64 and inserts('INSERT INTO sales'),
       'a normal sale stores one 64-character fingerprint and is saved')
    ok(any(sql.startswith('DELETE FROM sale_guard') for sql, _ in LOG), 'old guard rows are purged before the check')
check('double submit guard', t_double_submit)

def t_sale_errors():
    c = fresh()
    sale_post(c, payment_method='Bitcoin'); ok('Invalid payment method' in flashes(c)[-1], 'invalid payment method rejected')
    LOG.clear(); c.post('/sales/new', data={**F, 'payment_method': 'Cash'})
    ok('Please add at least one medicine with a valid quantity' in flashes(c)[-1], 'no medicine lines rejected')
    sale_post(c, **{'quantity[]': ['0']}); ok('Please add at least one medicine with a valid quantity' in flashes(c)[-1], 'zero quantity ignored')
    sale_post(c, **{'quantity[]': ['100001']}); ok('Quantity is too large' in flashes(c)[-1], 'huge quantity rejected')
    sale_post(c, **{'medicine_id[]': ['99']}); ok('no longer exists' in flashes(c)[-1], 'unknown medicine rejected')
    LOG.clear(); sale_post(c, **{'medicine_id[]': ['1', '99'], 'quantity[]': ['2', '1']})
    ok(not inserts('INSERT INTO sales') and 'no longer exists' in flashes(c)[-1],
       'one missing medicine blocks the whole bill (never billed silently without it)')
    LOG.clear(); sale_post(c, **{'medicine_id[]': ['1x'], 'quantity[]': ['1']})
    ok(not inserts('INSERT INTO sales') and 'Invalid medicine' in flashes(c)[-1], 'non-numeric medicine id rejected')
    LOG.clear(); sale_post(c, **{'medicine_id[]': ['3', '1', '2'], 'quantity[]': ['1', '1', '1']})
    ok([p for sql, p in LOG if sql.startswith('SELECT name, price, stock_quantity FROM medicines')] == [(1,), (2,), (3,)],
       'medicine rows locked in fixed id order (no deadlock between two sales)')
    sale_post(c, **{'quantity[]': ['500']}); ok('Insufficient stock for Panadol' in flashes(c)[-1], 'insufficient stock rejected')
    sale_post(c, **{'medicine_id[]': ['2'], 'quantity[]': ['10']})
    ok('Only 5 unexpired units of Brufen' in flashes(c)[-1], 'expired-only stock cannot be sold')
    sale_post(c, **{'quantity[]': ['abc']}); ok('Invalid number format!' in flashes(c)[-1], 'non-number quantity rejected')
    sale_post(c, paid_amount='-5'); ok('Paid amount must be between 0 and the total' in flashes(c)[-1], 'negative paid amount rejected')
    sale_post(c, paid_amount='abc'); ok('Invalid number format!' in flashes(c)[-1], 'non-number paid amount rejected')
    sale_post(c, discount='-1'); ok('Discount cannot be negative' in flashes(c)[-1], 'negative discount rejected')
    sale_post(c, discount='5', discount_type='percent', **{'quantity[]': ['1']})
    sale_post(c, discount='150', discount_type='percent'); ok('Discount cannot be more than 100%' in flashes(c)[-1], 'percent over 100 rejected')
    sale_post(c, discount='99999'); ok('Discount cannot be more than the bill amount' in flashes(c)[-1], 'discount above bill rejected')
    sale_post(c, paid_amount='50'); ok('needs a customer' in flashes(c)[-1], 'udhaar without customer rejected')
    Conn.rollbacks = 0
    STATE['raise_on'] = 'INSERT INTO sales'
    sale_post(c)
    STATE['raise_on'] = None
    ok(Conn.rollbacks >= 1 and 'Something went wrong' in flashes(c)[-1], 'database error rolls back and shows a safe message')
check('sale validation errors', t_sale_errors)

def t_sale_unit():
    c = fresh()
    sale_post(c, **{'medicine_id[]': ['3'], 'quantity[]': ['2']})
    items = inserts('INSERT INTO sale_items')
    ok(items and items[0][2] is None, 'medicine without batch records sells with no batch id')
    sale_post(c, **{'medicine_id[]': ['1'], 'quantity[]': ['2'], 'discount': '10', 'discount_type': 'percent'})
    ins = inserts('INSERT INTO sales')[0]
    ok(abs(float(ins[5]) - 20.0) < 0.01, 'percent discount 10% on Rs. 200 gives Rs. 20')
    sale_post(c, **{'medicine_id[]': ['1'], 'quantity[]': ['2'], 'discount': '30'})
    ok(abs(float(inserts('INSERT INTO sales')[0][5]) - 30.0) < 0.01, 'fixed discount is applied')
    sale_post(c, **{'medicine_id[]': ['1'], 'quantity[]': ['2'], 'paid_amount': '50', 'customer_id': '1'})
    ok(any('Balance (credit)' in m for m in flashes(c)), 'partial payment with a customer records the balance')
check('sale unit paths', t_sale_unit)

def t_sale_cashier_limit():
    c = fresh(settings=[dict(setting_key='cashier_max_discount', setting_value='5')])
    with c.session_transaction() as s: s['role'] = 'Cashier'
    sale_post(c, discount='10', discount_type='percent')
    ok('Cashier can give at most 5%' in flashes(c)[-1], 'cashier above the discount limit is refused')
check('cashier discount limit', t_sale_cashier_limit)

def t_sale_allergy_and_rx():
    c = fresh(history={'medical_history': 'Known Penicillin allergy'})
    sale_post(c, **{'medicine_id[]': ['4'], 'quantity[]': ['1'], 'customer_id': '1'})
    ok(any('Penicillin' in m or 'penicillin' in m.lower() for m in flashes(c)), 'allergy warning is shown before saving')
    reset(meds=dict(MEDS), batches=dict(BATCHES), rx=None); c = login('Admin')
    sale_post(c, prescription_id='77'); ok('Prescription not found' in flashes(c)[-1], 'unknown prescription rejected')
    reset(meds=dict(MEDS), batches=dict(BATCHES), rx=dict(prescription_id=5, customer_id=2, doctor_name='Ahmed'))
    c = login('Admin')
    sale_post(c, prescription_id='5', customer_id='9'); ok('belongs to another customer' in flashes(c)[-1], 'prescription of another customer rejected')
    sale_post(c, prescription_id='5', customer_id='2')
    ok(inserts('INSERT INTO sales')[0][9] == 5, 'sale is linked to the prescription')
check('sale allergy and prescription', t_sale_allergy_and_rx)

def t_prescription_get():
    reset(meds=dict(MEDS), batches=dict(BATCHES), rx=dict(prescription_id=5, customer_id=2, doctor_name='Ahmed'),
          rx_items=[dict(medicine_id=1, dosage='1 tab', medicine_name='Panadol', stock_quantity=60)], history=None)
    c = login('Admin')
    r = c.get('/sales/new?rx=5')
    ok(r.status_code == 200, 'prescription can be loaded into a new sale')
    reset(meds=dict(MEDS), batches=dict(BATCHES), rx=None); c = login('Admin')
    r = c.get('/sales/new?rx=404')   # flash is shown on this same page and then consumed
    ok(r.status_code == 200 and b'Prescription not found' in r.data, 'loading an unknown prescription shows a message')
check('prescription into sale', t_prescription_get)

# ---- payments -------------------------------------------------------------------------
def pay(c, sale_id=1, **kw):
    d = {'amount': '300', 'method': 'Cash'}; d.update(kw); LOG.clear()
    return c.post(f'/sales/{sale_id}/pay', data={**F, **d})

def t_pay():
    sale = dict(total_amount=D('1000'), returned_amount=D('0'), paid_amount=D('200'))
    c = fresh(sale=sale)
    pay(c); ok('Remaining balance: Rs. 500.00' in flashes(c)[-1], 'partial payment shows the remaining balance')
    ok(inserts('INSERT INTO sale_payments'), 'partial payment is recorded')
    pay(c, amount='800'); ok('Balance cleared.' in flashes(c)[-1], 'paying the full balance clears it')
    pay(c, method='Bitcoin'); ok('Please enter a valid amount' in flashes(c)[-1], 'unknown payment method rejected')
    pay(c, amount='abc'); ok('Please enter a valid amount' in flashes(c)[-1], 'non-number amount rejected')
    pay(c, amount='nan'); ok('Please enter a valid amount' in flashes(c)[-1], 'NaN amount rejected')
    pay(c, amount='0'); ok('Please enter a valid amount' in flashes(c)[-1], 'zero amount rejected')
    Conn.rollbacks = 0
    pay(c, amount='900'); ok('more than the balance' in flashes(c)[-1] and Conn.rollbacks == 1, 'overpayment rejected and rolled back')
    c2 = fresh(sale=None); pay(c2); ok('Sale not found' in flashes(c2)[-1], 'payment for a missing sale shows a message')
    c3 = fresh(sale=sale, raise_on='UPDATE sales SET paid_amount'); pay(c3)
    ok('Something went wrong' in flashes(c3)[-1], 'database error during payment shows a safe message')
    c4 = login('Cashier'); LOG.clear()
    c4.post('/sales/1/pay', data={**F, 'amount': '10', 'method': 'Cash'})
    ok(not inserts('UPDATE sales SET paid_amount') and not inserts('INSERT INTO sale_payments'),
       'cashier cannot receive payments')
check('receive payment', t_pay)

# ---- returns --------------------------------------------------------------------------
def ret_post(c, **kw):
    d = {**F, 'ret_5': '1', 'reason': 'Damaged'}; d.update(kw); LOG.clear()
    return c.post('/sales/1/return', data=d)

def t_return():
    c = fresh(sale=dict(SALE), items=[dict(x) for x in RET_ITEMS])
    r = c.get('/sales/1/return'); ok(r.status_code == 200 and 'Panadol' in r.get_data(as_text=True), 'return page shows the items')
    c = fresh(sale=None); c.get('/sales/1/return'); ok('Sale not found' in flashes(c)[-1], 'return for a missing sale shows a message')
    c = fresh(sale=dict(SALE), items=[dict(x) for x in RET_ITEMS])
    ret_post(c, ret_5='0'); ok('Please enter the quantity of at least one item' in flashes(c)[-1], 'no quantity chosen is refused')
    ret_post(c, ret_5='9'); ok('You can return at most 3 of Panadol' in flashes(c)[-1], 'more than returnable is refused')
    ret_post(c, ret_5='-1'); ok('You can return at most' in flashes(c)[-1], 'negative quantity is refused')
    ret_post(c, ret_5='x'); ok('Invalid number format!' in flashes(c)[-1], 'non-number quantity is refused')
    r = ret_post(c, ret_5='1')
    ok(r.status_code == 302 and '/invoice/1' in r.headers['Location'], 'valid return redirects to the invoice')
    ok(any('Give Rs. 100.00 back' in m for m in flashes(c)), 'paid customer is told the cash to give back')
    ok(inserts('INSERT INTO sale_return_items') and inserts('INSERT INTO stock_adjustments'), 'return writes items and stock adjustment')
    c = fresh(sale=dict(SALE, paid_amount=D('0')), items=[dict(x) for x in RET_ITEMS])
    ret_post(c, ret_5='1')
    ok(any('taken off the customer balance' in m for m in flashes(c)), 'unpaid sale: refund reduces the balance instead')
    c = fresh(sale=dict(SALE), items=[dict(x) for x in RET_ITEMS], raise_on='INSERT INTO sale_returns')
    ret_post(c, ret_5='1'); ok('Something went wrong' in flashes(c)[-1], 'database error during return shows a safe message')
check('sale return', t_return)

# ---- invoices -------------------------------------------------------------------------
def t_invoice():
    inv = [dict(medicine_name='Panadol', quantity=2, unit_price=D('100'), subtotal=D('200'))]
    pays = [dict(amount=D('200'), method='Cash', created_at=datetime(2026, 10, 12))]
    c = fresh(sale=dict(SALE), inv_items=inv, payments=pays)
    r = c.get('/invoice/1'); ok(r.status_code == 200 and 'Panadol' in r.get_data(as_text=True), 'invoice shows items')
    r = c.get('/invoice/1/thermal'); ok(r.status_code == 200, 'thermal receipt renders')
    c = fresh(sale=None)
    c.get('/invoice/1'); ok('Invoice not found' in flashes(c)[-1], 'missing invoice shows a message')
    c.get('/invoice/1/thermal'); ok('Invoice not found' in flashes(c)[-1], 'missing thermal receipt shows a message')
check('invoices', t_invoice)

# ---- lib.py ---------------------------------------------------------------------------
def in_ctx(fn, url='/reports'):
    with A.app.test_request_context(url):
        flask_session['user_id'] = 1
        return fn()

def t_lib_basics():
    ok(_valid_date('2026-10-05') == '2026-10-05' and _valid_date('bad') == '' and _valid_date(None) == '', '_valid_date accepts only YYYY-MM-DD')
    ok(_num('') == 0.0 and _num(' 2.5 ') == 2.5 and _num(None, 7) == 7, '_num parses text with defaults')
    try:
        _num('nan'); ok(False, '_num rejects NaN')
    except ValueError:
        ok(True, '_num rejects NaN')
    ok(_like('a%b_c').startswith('%') and '\\%' in _like('a%b_c') and '\\_' in _like('a%b_c'), '_like escapes wildcard characters')
    ok(_as_date(datetime(2026, 10, 3, 9)) == date(2026, 10, 3) and _as_date(date(2026, 10, 4)) == date(2026, 10, 4)
       and _as_date('2026-10-05 10:00:00') == date(2026, 10, 5), '_as_date handles datetime, date and text')
    ok(_clean_doctor('Dr. Ahmed') == 'Ahmed' and _clean_doctor('dr.ahmed') == 'ahmed' and _clean_doctor('Drake') == 'Drake',
       '_clean_doctor strips the title only')
    ok(doctor_label('Dr. Ahmed') == 'Dr. Ahmed' and doctor_label('') == 'Dr. -', 'doctor_label builds the display name')
    ok(_audit_json(None) is None and _audit_json({'a': 1}) == '{"a": 1}' and len(_audit_json({'x': 'y' * 70000})) == 60000,
       '_audit_json returns None, JSON, and caps the length')
check('lib basics', t_lib_basics)

def t_lib_return_items():
    reset(items=[dict(sale_item_id=5, medicine_id=1, batch_id=11, quantity=3, unit_price=D('100'), name='Panadol', returned_qty=1)])
    def go():
        cur = Conn().cursor(); cur.execute('SELECT ...', (1,))
        return _return_items(cur, 1, 0.5)
    items = go()
    ok(items[0]['returned_qty'] == 1 and items[0]['returnable'] == 2 and items[0]['unit_refund'] == 50.0,
       '_return_items computes returnable quantity and refund per unit')
check('return items helper', t_lib_return_items)

def t_lib_settings():
    reset(settings=[dict(setting_key='shop_name', setting_value='Care Pharmacy'),
                    dict(setting_key='tax_rate', setting_value=None)])
    s = get_all_settings()
    ok(s['shop_name'] == 'Care Pharmacy' and s['tax_rate'] == str(A.Config.TAX_RATE), 'saved settings override defaults, NULL values ignored')
    ok(get_setting('shop_name') == 'Care Pharmacy' and get_setting('no_such_key') == '', 'get_setting falls back to defaults')
    reset(settings=[dict(setting_key='tax_rate', setting_value='16'), dict(setting_key='cashier_max_discount', setting_value='7')])
    ok(get_tax_rate() == 16.0 and get_cashier_max() == 7.0, 'tax and cashier limits read from settings')
    reset(settings=[dict(setting_key='tax_rate', setting_value='abc'), dict(setting_key='cashier_max_discount', setting_value='x')])
    ok(get_tax_rate() == float(A.Config.TAX_RATE) and get_cashier_max() == float(A.Config.CASHIER_MAX_DISCOUNT_PCT),
       'bad setting values fall back to config')
    reset(settings=[])
    shop = in_ctx(lambda: inject_shop()['shop'], url='/dashboard')
    ok(shop['name'] == 'MEDIGEN' and 'footer' in shop, 'inject_shop gives the shop name to every page')
    def boom(*a, **k): raise RuntimeError('no db')
    orig = Cur.execute
    def failing(self, sql, p=None):
        if 'app_settings' in sql: raise RuntimeError('no table')
        return orig(self, sql, p)
    Cur.execute = failing
    try:
        ok(get_all_settings()['shop_name'] == 'MEDIGEN', 'settings read failure returns defaults instead of raising')
    finally:
        Cur.execute = orig
check('settings helpers', t_lib_settings)

def t_lib_reports():
    r = in_ctx(lambda: _report_dates(), url='/reports?start_date=2026-10-10&end_date=2026-10-01')
    ok(r == ('2026-10-01', '2026-10-10'), '_report_dates swaps reversed dates')
    s, e = in_ctx(lambda: _report_dates(), url='/reports?start_date=xx')
    ok(s < e and (date.fromisoformat(e) - date.fromisoformat(s)).days == 29, 'bad start date falls back to the last 30 days')
    reset(daily=DAILY, period_items=PERIOD)
    cur = Conn().cursor()
    f = _sales_figures(cur, '2026-10-01', '2026-10-31')
    ok(abs(f['total_revenue'] - 400) < 0.01 and f['total_invoices'] == 3, 'sales figures sum revenue and invoices')
    # Panadol 3 + Panadol 1 = 4 units at cost 60 each = 240; the fully returned Brufen line adds nothing
    ok(f['total_items'] == 4 and abs(f['total_cost'] - 240) < 0.01, 'fully returned line is skipped in items and cost')
    ok(abs(f['total_profit'] - 160) < 0.01 and abs(f['margin_pct'] - 40) < 0.01, 'profit and margin are revenue minus cost')
    ok(f['best'][0]['name'] == 'Panadol' and f['profit_rows'][0]['name'] == 'Panadol', 'best sellers and profit rows are sorted')
    reset(daily=[], period_items=[])
    f = _sales_figures(Conn().cursor(), '2026-10-01', '2026-10-31')
    ok(f['margin_pct'] == 0.0 and f['avg_invoice'] == 0.0 and f['profit_rows'] == [], 'no sales gives zero figures, no division error')
check('report figures', t_lib_reports)

def t_lib_lists_and_csv():
    reset(low=[dict(name='Panadol', stock_quantity=2, reorder_level=10)],
          expiry=[dict(name='Brufen', batch_number='B1', expiry_date=date(2026, 11, 1), quantity=4)])
    cur = Conn().cursor()
    ok(len(_stock_rows(cur)) == 1 and _expiry_rows(cur)[0]['batch_number'] == 'B1', 'stock and expiry rows are read')
    def csv_text():
        resp = _csv_response(['Name', 'Qty'], [['Panadol', 2]], 'stock.csv')
        return resp.status_code, resp.headers.get('Content-Disposition'), resp.get_data(as_text=True)
    code, disp, body = in_ctx(csv_text)
    ok(code == 200 and 'stock.csv' in disp and body.startswith('﻿') and 'Panadol' in body, 'CSV export has a BOM, the header and the file name')
check('lists and csv', t_lib_lists_and_csv)

def t_lib_flash_audit():
    def fl():
        flash_unexpected('Save failed.')
        return [m for _, m in flask_session.get('_flashes', [])]
    msgs = in_ctx(fl)
    ok(any(m.startswith('Save failed.') and 'Please try again' in m for m in msgs), 'flash_unexpected shows a short safe message')
    def au():
        audit(Conn().cursor(), 'sale.test', 'sale', 1, 'detail', after={'x': 1})
        audit_direct('login.test', 'detail', user_id=1, username='Ahmed')
    LOG.clear(); in_ctx(au, url='/sales/new')
    ok(sum(1 for sql, _ in LOG if sql.startswith('INSERT INTO audit_log')) == 2, 'audit and audit_direct both write audit rows')
check('flash and audit', t_lib_flash_audit)

def t_lib_allergy():
    ok(allergy_warnings('Known Penicillin allergy', ['Amoxicillin 500']) != [], 'penicillin history warns about amoxicillin')
    ok(allergy_warnings('Asthma', ['Brufen']) != [], 'asthma history warns about brufen')
    ok(allergy_warnings('Aspirin allergy', ['Aspirin']) != [], 'aspirin history warns about aspirin')
    ok(allergy_warnings('Sulfa allergy', ['Bactrim DS']) != [], 'sulfa history warns about cotrimoxazole brands')
    ok(allergy_warnings('', ['Panadol']) == [] and allergy_warnings('Kidney', []) == [], 'no history or no medicines gives no warnings')
    ok(len(allergy_warnings('Penicillin', ['Amoxicillin', 'Amoxicillin'])) == len(set(allergy_warnings('Penicillin', ['Amoxicillin', 'Amoxicillin']))),
       'duplicate warnings are removed')
check('allergy rules', t_lib_allergy)

# ---- summary ----------------------------------------------------------------------------
os_chdir = _os.chdir(_cwd) if False else None
passed = sum(1 for _, r in RESULTS if r); failed = len(RESULTS) - passed
print(f"\nTOTAL: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
