"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, types, os, re
from decimal import Decimal
from datetime import date, datetime, timedelta
sys.path.insert(0,ROOT); os.chdir(ROOT)
bc=types.ModuleType('bcrypt'); bc.gensalt=lambda *a,**k:b''; bc.hashpw=lambda p,s:b'h:'+p; bc.checkpw=lambda p,h:h==b'h:'+p
sys.modules['bcrypt']=bc
D=Decimal
MEDS={'1':dict(name='Panadol',price=D('100.00'),stock_quantity=60),
      '2':dict(name='Brufen',price=D('50.00'),stock_quantity=30),
      '3':dict(name='OldMed',price=D('10.00'),stock_quantity=5)}
BATCHES={'1':[dict(batch_id=11,quantity=20),dict(batch_id=12,quantity=40)],   # fresh batches, oldest first
         '2':[dict(batch_id=21,quantity=5)],                                    # only 5 fresh although stock is 30 (rest expired)
         '3':[]}
BCOUNT={'1':2,'2':2,'3':0}
ST={'sale':None,'items':[],'newstock':50}
class Cur:
    log=[]; lastrowid=100
    def execute(self,sql,p=None): self.sql=" ".join(sql.split()); self.p=p; Cur.log.append((self.sql,p))
    def fetchone(self):
        s=self.sql; p=self.p
        if 'information_schema' in s: return {'n':1}
        if s.startswith('SELECT * FROM cash_sessions WHERE closed_at IS NULL'): return {'session_id': 1, 'opened_at': None, 'opening_amount': 0, 'closed_at': None}  # v87.03: drawer open
        if s.startswith('SELECT name, price, stock_quantity FROM medicines'): return MEDS.get(str(p[0]))
        if s.startswith('SELECT COUNT(*) AS n FROM batches WHERE medicine_id'): return {'n':BCOUNT[str(p[0])]}
        if s.startswith('SELECT total_amount, returned_amount, paid_amount FROM sales'): return ST['sale']
        if s.startswith('SELECT s.*, c.name AS customer_name'): return ST['sale']
        if s.startswith('SELECT stock_quantity FROM medicines'): return {'stock_quantity':ST['newstock']}
        if s.startswith('SELECT COUNT(*) AS total'): return {'total':45}
        if 'AS cnt' in s: return dict(cnt=3,revenue=D('4500.00'))
        if 'AS dues' in s: return dict(dues=D('1200.00'),due_count=D(2))
        if s.startswith('SELECT s.*, c.name AS customer_name, c.contact_number'): return ST['sale']
        return None
    def fetchall(self):
        s=self.sql; p=self.p
        if 'AND quantity > 0 AND expiry_date >= CURDATE()' in s and 'FOR UPDATE' in s: return BATCHES[str(p[0])]
        if s.startswith('SELECT si.sale_item_id'): return [dict(x) for x in ST['items']]
        if s.startswith('SELECT s.*, c.name AS customer_name, u.full_name AS cashier'):
            return [dict(sale_id=7,sale_date=datetime(2026,10,12,10,0),customer_name='Ali',cashier='Ahmed',total_amount=D('1000.00'),paid_amount=D('200.00'),returned_amount=D('100.00'),
                         payment_method='Cash',due_amount=D('700.00')),
                    dict(sale_id=6,sale_date=datetime(2026,10,11,10,0),customer_name=None,cashier='Ahmed',total_amount=D('500.00'),paid_amount=D('500.00'),returned_amount=D('0.00'),payment_method='Card',due_amount=D('0.00'))]
        if s.startswith('SELECT m.medicine_id, m.name, m.barcode, m.price, m.stock_quantity'):
            return [dict(medicine_id=1,name='Panadol',price=D('100'),stock_quantity=60,fresh_qty=D(60),batch_count=2),
                    dict(medicine_id=2,name='Brufen',price=D('50'),stock_quantity=30,fresh_qty=D(5),batch_count=2),
                    dict(medicine_id=3,name='Dead',price=D('9'),stock_quantity=8,fresh_qty=D(0),batch_count=1)]
        if s.startswith('SELECT c.customer_id, c.name'): return [dict(customer_id=1,name='Ali',due=D('700')),dict(customer_id=2,name='Sara',due=D('0'))]
        if s.startswith('SELECT m.name AS medicine_name, SUM(si.quantity)'): return [dict(medicine_name='Panadol',quantity=D(3),unit_price=D('100.00'),subtotal=D('300.00'))]
        if s.startswith('SELECT amount, method, created_at FROM sale_payments'): return [dict(amount=D('200'),method='Cash',created_at=datetime(2026,10,12)),dict(amount=D('100'),method='Card',created_at=datetime(2026,10,13))]
        return []
    def close(self): pass
class Conn:
    rb=0
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): Conn.rb+=1
m=types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self,app): self.connection=Conn()
m.MySQL=MySQL; sys.modules['flask_mysqldb']=m
import app as A
A.app.template_folder=(ROOT + '/templates')
ok=lambda c,msg: print(('PASS ' if c else 'FAIL ')+msg)
def login(role='Admin'):
    c=A.app.test_client(); c.get('/login')
    with c.session_transaction() as s: s.update(user_id=1,user_name='Ahmed',role=role); s['_csrf']='t'
    return c
F={'csrf_token':'t'}
def ins(prefix): return [p for x,p in Cur.log if x.startswith(prefix)]
def flashes(c):
    with c.session_transaction() as s: return [m for _,m in s.get('_flashes',[])]
def sale(c,**kw):
    d={**F,'payment_method':'Cash','medicine_id[]':['1'],'quantity[]':['30']}; d.update(kw); Cur.log.clear(); Conn.rb=0
    return c.post('/sales/new',data=d)

c=login('Admin')
r=sale(c); sales_ins=ins('INSERT INTO sales')[0]; items=ins('INSERT INTO sale_items')
ok(r.status_code==302 and '/invoice/100' in r.headers['Location'],'sale saved -> opens receipt')
ok(len(items)==2 and items[0][3]==20 and items[0][2]==11 and items[1][3]==10 and items[1][2]==12,'30 units split FIFO: 20 from oldest batch 11 + 10 from batch 12')
ok(sales_ins[3]==3000.0 and sales_ins[4]==3000.0 and sales_ins[8]==3000.0,'total = subtotal = paid = 3000 (full payment by default)')
ok(len(ins('INSERT INTO sale_payments'))==1,'payment row saved')
ok(any('expiry_date >= CURDATE()' in x for x,_ in Cur.log),'expired batches excluded from selling')

r=sale(c,**{'medicine_id[]':['2'],'quantity[]':['10']}); ok(not ins('INSERT INTO sales') and any('unexpired' in m for m in flashes(c)),'only 5 fresh units of Brufen -> blocked (expired stock not sold)')
r=sale(c,**{'medicine_id[]':['3'],'quantity[]':['2']}); it=ins('INSERT INTO sale_items'); ok(it and it[0][2] is None,'medicine without batch records -> sold with batch NULL')
r=sale(c,**{'medicine_id[]':['1','1'],'quantity[]':['5','5']}); it=ins('INSERT INTO sale_items'); ok(sum(x[3] for x in it)==10,'same medicine twice -> merged (10 units)')
r=sale(c,**{'quantity[]':['999']}); ok(not ins('INSERT INTO sales'),'quantity above stock rejected')

A.Config.TAX_RATE=10.0; A.SETTING_DEFAULTS['tax_rate']='10.0'
r=sale(c,discount='10',discount_type='percent',**{'quantity[]':['10']}); s=ins('INSERT INTO sales')[0]
ok(s[4]==1000.0 and s[5]==100.0 and s[7]==90.0 and s[3]==990.0,f'1000 - 10% = 900 + 10% tax 90 = 990 (got subtotal {s[4]}, disc {s[5]}, tax {s[7]}, total {s[3]})')
r=sale(c,discount='50',discount_type='amount',**{'quantity[]':['10']}); s=ins('INSERT INTO sales')[0]; ok(s[5]==50.0 and s[3]==1045.0,'discount in Rs. 50 -> total 1045')
A.Config.TAX_RATE=0.0; A.SETTING_DEFAULTS['tax_rate']='0.0'
r=sale(c,discount='5000',discount_type='amount'); ok(not ins('INSERT INTO sales'),'discount bigger than bill rejected')
r=sale(c,discount='150',discount_type='percent'); ok(not ins('INSERT INTO sales'),'discount above 100% rejected')

cc=login('Cashier')
r=sale(cc,discount='20',discount_type='percent',**{'quantity[]':['10']}); ok(not ins('INSERT INTO sales') and any('at most' in m for m in flashes(cc)),'Cashier 20% discount blocked (limit 10%)')
r=sale(cc,discount='10',discount_type='percent',**{'quantity[]':['10']}); ok(len(ins('INSERT INTO sales'))==1,'Cashier 10% discount allowed')

r=sale(c,paid_amount='1000',**{'quantity[]':['30']}); ok(not ins('INSERT INTO sales') and any('credit' in m for m in flashes(c)),'credit sale without customer rejected')
r=sale(c,paid_amount='1000',customer_id='1',**{'quantity[]':['30']}); s=ins('INSERT INTO sales')[0]; ok(s[8]==1000.0 and s[3]==3000.0,'udhaar with customer: total 3000, paid 1000 (balance 2000)')
r=sale(c,paid_amount='0',customer_id='1'); ok(len(ins('INSERT INTO sales'))==1 and not ins('INSERT INTO sale_payments'),'nothing paid -> no payment row')
r=sale(c,paid_amount='99999',customer_id='1'); ok(not ins('INSERT INTO sales'),'paid more than total rejected')
r=sale(c,paid_amount='abc',customer_id='1'); ok(not ins('INSERT INTO sales'),'text in amount rejected (no crash)')
ok(c.post('/sales/new',data={**F,'payment_method':'Cash','medicine_id[]':[''],'quantity[]':['']}).status_code==302 and not ins('INSERT INTO sales'),'empty sale rejected')

h=c.get('/sales/new').get_data(as_text=True)
ok('data-stock="60"' in h and 'data-stock="5"' in h,'sale form: stock shown = unexpired units only (Brufen 5, not 30)')
ok('Dead' not in h and 'owes Rs. 700' in h,'sale form: fully expired medicine hidden, customer due shown')
ok('Cashier can give' in cc.get('/sales/new').get_data(as_text=True),'cashier sees discount limit hint')

# list
Cur.log.clear(); h=c.get('/sales?filter=due&q=42&from=2026-10-01&to=2026-10-12&page=2').get_data(as_text=True)
sq=" ".join(x for x,_ in Cur.log)
lim=[p for x,p in Cur.log if 'LIMIT %s OFFSET %s' in x][0]
ok('0.004' in sq and 's.sale_id = %s' in sq and 'DATE(s.sale_date) >= %s' in sq,'sales list: due filter, invoice-no search, date range in SQL')
ok(lim[-2:]==[15,15] and 42 in lim,'sales list: page 2 at 15 per page -> offset 15, invoice no 42')
ok('Due Rs. 700.00' in h and 'Receive' in h and 'returned 100.00' in h and '>Paid<' in h,'sales list: due / paid / returned badges + Receive button')
ok('Rs. 1,200' in h,'pending balances card')
ok(cc.get('/sales').get_data(as_text=True).count('btn-mini"') == 0 or 'Return</a>' not in cc.get('/sales').get_data(as_text=True),'Cashier has no Return button')

# receive payment
ST['sale']=dict(total_amount=D('1000.00'),returned_amount=D('100.00'),paid_amount=D('200.00'))   # due 700
Cur.log.clear(); c.post('/sales/7/pay',data={**F,'amount':'800','method':'Cash'}); ok(not ins('UPDATE sales SET paid_amount'),'payment above balance rejected')
Cur.log.clear(); c.post('/sales/7/pay',data={**F,'amount':'300','method':'Online'}); ok(ins('UPDATE sales SET paid_amount')==[(300.0,7)] and ins('INSERT INTO sale_payments')[0][2:]==(300.0,'Online'),'payment of 300 saved (balance 700 -> 400)')
Cur.log.clear(); c.post('/sales/7/pay',data={**F,'amount':'-5','method':'Cash'}); ok(not ins('UPDATE sales SET paid_amount'),'negative payment rejected')
Cur.log.clear(); c.post('/sales/7/pay',data={**F,'amount':'5','method':'Bitcoin'}); ok(not ins('UPDATE sales SET paid_amount'),'unknown payment method rejected')

# returns
def item(i,mid,bid,qty,price,retq=0): return dict(sale_item_id=i,medicine_id=mid,batch_id=bid,quantity=qty,unit_price=D(str(price)),name='Panadol',returned_qty=retq)
ST['items']=[item(1,1,11,20,100),item(2,1,12,10,100)]
ST['sale']=dict(sale_id=7,total_amount=D('3000.00'),subtotal_amount=D('3000.00'),discount_amount=D('0'),paid_amount=D('3000.00'),returned_amount=D('0.00'),customer_name='Ali',sale_date=datetime(2026,10,12))
h=c.get('/sales/7/return').get_data(as_text=True); ok('name="ret_1"' in h and 'max="20"' in h and 'max="10"' in h,'return page lists items with max quantity')
ok(cc.get('/sales/7/return').status_code==302,'Cashier cannot open returns (Admin / Pharmacist only)')
Cur.log.clear(); ST['newstock']=47
r=c.post('/sales/7/return',data={**F,'ret_1':'3','ret_2':'0','reason':'wrong medicine'})
ok(ins('UPDATE medicines SET stock_quantity = stock_quantity + %s')==[(3,1)] and ins('UPDATE batches SET quantity = quantity + %s')==[(3,11)],'return: stock +3 and batch 11 +3')
ok(ins('INSERT INTO stock_adjustments')[0][2:5]==(3,44,47),'return written in stock history (44 -> 47)')
up=ins('UPDATE sales SET returned_amount')[0]; ok(up==(300.0,2700.0,7),f'fully paid sale: refund 300 returned, customer gets 300 cash back, paid 3000 -> 2700 {up}')
# credit sale: total 3000, paid 200, return 300 -> no cash back, balance reduced
ST['sale']=dict(sale_id=7,total_amount=D('3000.00'),subtotal_amount=D('3000.00'),discount_amount=D('0'),paid_amount=D('200.00'),returned_amount=D('0.00'),customer_name='Ali',sale_date=datetime(2026,10,12))
Cur.log.clear(); c.post('/sales/7/return',data={**F,'ret_1':'3'}); up=ins('UPDATE sales SET returned_amount')[0]
ok(up==(300.0,200.0,7),f'udhaar sale: no cash back, balance reduced instead {up}')
# discount shared: total 2700 for subtotal 3000 -> ratio .9
ST['sale']=dict(sale_id=7,total_amount=D('2700.00'),subtotal_amount=D('3000.00'),discount_amount=D('300'),paid_amount=D('2700.00'),returned_amount=D('0.00'),customer_name='Ali',sale_date=datetime(2026,10,12))
Cur.log.clear(); c.post('/sales/7/return',data={**F,'ret_1':'10'}); ok(ins('UPDATE sales SET returned_amount')[0][0]==900.0,'10 units x 100 x 0.9 (discount shared) = refund 900')
Cur.log.clear(); c.post('/sales/7/return',data={**F,'ret_1':'21'}); ok(not ins('INSERT INTO sale_returns'),'cannot return more than sold')
ST['items']=[item(1,1,11,20,100,retq=18)]
Cur.log.clear(); c.post('/sales/7/return',data={**F,'ret_1':'3'}); ok(not ins('INSERT INTO sale_returns'),'cannot return more than what is left after earlier returns')
Cur.log.clear(); c.post('/sales/7/return',data={**F,'ret_1':'0'}); ok(not ins('INSERT INTO sale_returns'),'return with nothing selected rejected')
Cur.log.clear(); c.post('/sales/7/return',data={**F,'ret_1':'x'}); ok(not ins('INSERT INTO sale_returns'),'text quantity rejected (no crash)')

# invoice
ST['sale']=dict(sale_id=7,sale_date=datetime(2026,10,12),customer_name='Ali',contact_number='0300',email=None,cashier='Ahmed',payment_method='Cash',
                subtotal_amount=D('3000.00'),discount_amount=D('300.00'),tax_rate=D('10.00'),tax_amount=D('270.00'),total_amount=D('2970.00'),paid_amount=D('1000.00'),returned_amount=D('100.00'),due_amount=D('1870.00'))
h=c.get('/invoice/7').get_data(as_text=True)
ok('Discount' in h and '- Rs. 300.00' in h and 'Tax (10.00%)' in h and 'Balance due' in h and 'Rs. 1870.00' in h and 'Returned items' in h,'receipt shows subtotal, discount, tax, returned, paid, balance due')
ok('Return items' in h and 'Payments:' in h,'receipt shows Return button + payment history')
ok('Return items' not in cc.get('/invoice/7').get_data(as_text=True),'Cashier does not see Return button on receipt')
