"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, types, os, re
from decimal import Decimal
from datetime import datetime
sys.path.insert(0,ROOT); os.chdir(ROOT)
bc=types.ModuleType('bcrypt'); bc.gensalt=lambda *a,**k:b''; bc.hashpw=lambda p,s:b'h:'+p; bc.checkpw=lambda p,h:h==b'h:'+p
sys.modules['bcrypt']=bc
D=Decimal
MEDNAMES={1:'Amoxicillin',2:'Panadol',3:'Brufen'}
ST={'hist':'','rx':None,'rx_items':[],'rx_cust':1,'dispensed':0,'rx_doctor':'Bilal','rx_fetch':None}
class Cur:
    log=[]; lastrowid=55
    def execute(self,sql,p=None):
        self.sql=" ".join(sql.split()); self.p=p; Cur.log.append((self.sql,p))
    def fetchone(self):
        s=self.sql; p=self.p
        if 'information_schema' in s: return {'n':1}
        if s.startswith('SELECT * FROM cash_sessions WHERE closed_at IS NULL'): return {'session_id': 1, 'opened_at': None, 'opening_amount': 0, 'closed_at': None}  # v87.03: drawer open
        if s.startswith('SELECT customer_id, medical_history FROM customers'):
            return dict(customer_id=int(p[0]),medical_history=ST['hist']) if p and p[0] in ('1','2') else None
        if s.startswith('SELECT name FROM medicines WHERE medicine_id'):
            return {'name':MEDNAMES[int(p[0])]} if p and int(p[0]) in MEDNAMES else None
        if s.startswith('SELECT COUNT(*) AS total FROM prescriptions') or s.startswith('SELECT COUNT(*) AS total FROM prescriptions p JOIN'):
            return {'total':30}
        if 'SUM((SELECT COUNT' in s: return {'total':30,'dispensed':D(12)}
        if s.startswith('SELECT COUNT(*) AS n FROM sales WHERE prescription_id'): return {'n':ST['dispensed']}
        if s.startswith('SELECT prescription_id, customer_id FROM prescriptions WHERE prescription_id'):
            return ST['rx_fetch']
        if s.startswith('SELECT prescription_id, customer_id, doctor_name FROM prescriptions WHERE'):
            return dict(prescription_id=5,customer_id=ST['rx_cust'],doctor_name=ST['rx_doctor']) if p[0]==5 else None
        if s.startswith('SELECT p.*, c.name AS customer_name, c.contact_number'):
            return dict(prescription_id=5,customer_name='Ali',contact_number='0300',email=None,doctor_name=ST['rx_doctor'],date_issued=datetime(2026,10,13).date(),notes='rest')
        if s.startswith('SELECT medical_history FROM customers'): return {'medical_history':ST['hist']}
        if s.startswith('SELECT m.medicine_id, m.name, m.barcode, m.price, m.stock_quantity'): return None
        if 'AND quantity > 0 AND expiry_date >= CURDATE()' in s: return None
        if s.startswith('SELECT COUNT(*) AS n FROM batches'): return {'n':0}
        if s.startswith('SELECT name, price, stock_quantity FROM medicines'):
            nm={'2':'Panadol','3':'Brufen'}.get(str(p[0]),'Amoxicillin')
            return {'name':nm,'price':D('100'),'stock_quantity':50}
        return None
    def fetchall(self):
        s=self.sql; p=self.p
        if s.startswith('SELECT p.*, c.name AS customer_name, (SELECT') or 'pi.prescription_id = p.prescription_id) AS item_count' in s:
            return [dict(prescription_id=5,date_issued=datetime(2026,10,13).date(),customer_name='Ali',doctor_name='Dr. Bilal',item_count=2,dispensed_count=0,sale_id=None),
                    dict(prescription_id=4,date_issued=datetime(2026,10,12).date(),customer_name='Sara',doctor_name='Ahmed',item_count=1,dispensed_count=1,sale_id=77)]
        if s.startswith('SELECT pi.medicine_id, pi.dosage, m.name AS medicine_name'):
            return ST['rx_items']
        if s.startswith('SELECT pi.*, m.name AS medicine_name'):
            return [dict(medicine_name='Amoxicillin',dosage='1 tablet twice a day',duration_days=5),dict(medicine_name='Panadol',dosage='1 tablet',duration_days=3)]
        if s.startswith('SELECT sale_id, sale_date, total_amount FROM sales WHERE prescription_id'):
            return [dict(sale_id=77,sale_date=datetime(2026,10,12),total_amount=D('300'))] if ST['dispensed'] else []
        if s.startswith('SELECT customer_id, name, medical_history FROM customers'):
            return [dict(customer_id=1,name='Ali',medical_history='allergic to penicillin'),dict(customer_id=2,name='Sara',medical_history='asthma')]
        if s.startswith('SELECT medicine_id, name FROM medicines'):
            return [dict(medicine_id=1,name='Amoxicillin'),dict(medicine_id=2,name='Panadol'),dict(medicine_id=3,name='Brufen')]
        if s.startswith('SELECT m.medicine_id, m.name, m.barcode, m.price, m.stock_quantity'):
            return [dict(medicine_id=1,name='Amoxicillin',price=D('100'),stock_quantity=50,fresh_qty=D(50),batch_count=0,available=50),
                    dict(medicine_id=2,name='Panadol',price=D('100'),stock_quantity=50,fresh_qty=D(50),batch_count=0,available=50),
                    dict(medicine_id=3,name='Brufen',price=D('50'),stock_quantity=0,fresh_qty=D(0),batch_count=0,available=0)]
        if s.startswith('SELECT c.customer_id, c.name'): return [dict(customer_id=1,name='Ali',due=D(0)),dict(customer_id=2,name='Sara',due=D(0))]
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
    with c.session_transaction() as s: s.update(user_id=1,user_name='A',role=role); s['_csrf']='t'
    return c
def flashes(c):
    with c.session_transaction() as s: return [m for _,m in s.get('_flashes',[])]
def ins(prefix): return [p for x,p in Cur.log if x.startswith(prefix)]
F={'csrf_token':'t'}
c=login()

# ---- doctor label ----
L=A.doctor_label
ok(L('Ahmed')=='Dr. Ahmed' and L('Dr. Bilal')=='Dr. Bilal' and L('dr.bilal')=='Dr. bilal' and L('Dr.Ahmed')=='Dr. Ahmed','doctor label: no double "Dr." (Ahmed / Dr. Bilal / dr.bilal / Dr.Ahmed)')
ok(L('Drake')=='Dr. Drake' and L('')=='Dr. -','doctor label keeps names like "Drake"; empty -> "Dr. -"')

# ---- allergy warnings (pure function) ----
W=A.allergy_warnings
ok(any('penicillin' in x and 'Amoxicillin' in x for x in W('allergic to penicillin',['Amoxicillin 500mg'])),'penicillin history -> amoxicillin warning')
ok(W('allergic to penicillin',['Panadol'])==[],'penicillin history -> no warning for Panadol')
ok(any('asthma' in x for x in W('asthma',['Brufen'])),'asthma history -> Brufen (NSAID) warning')
ok(any('Panadol' in x for x in W('had panadol reaction',['Panadol'])),'medicine named in history -> warning')
ok(W('',['Panadol'])==[] and W(None,['Panadol'])==[],'empty history -> no warnings, no crash')
ok(len(W('asthma',['Brufen','Brufen']))==len(set(W('asthma',['Brufen','Brufen']))),'duplicate warnings removed')

# ---- prescriptions list ----
Cur.log.clear(); h=c.get('/prescriptions?q=ali&filter=open&page=1').get_data(as_text=True)
ok(h.count('Dispense')>=1 and 'Dispensed' in h and 'sale #77' in h,'list: Dispense button for open, Sale link for dispensed')
ok('Dr. Bilal' in h and 'Dr. Dr.' not in h,'list: no "Dr. Dr." on stored "Dr. Bilal"')
sq=" ".join(x for x,_ in Cur.log); ok('c.name LIKE' in sq and '= 0' in sq,'list: search + open filter in SQL')
ok(c.get('/prescriptions').status_code==200 and login('Cashier').get('/prescriptions').status_code==302,'Admin/Pharmacist only (cashier redirected)')

# ---- add prescription: valid ----
Cur.log.clear(); ST['hist']='allergic to penicillin'
r=c.post('/prescriptions/add',data={**F,'customer_id':'1','doctor_name':'Dr. Bilal','notes':'rest',
          'medicine_id[]':['1','2',''],'dosage[]':['1 tablet twice a day','1 tablet',''],'duration[]':['5','3','']})
ok(r.status_code==302,'valid prescription saved')
ok(ins('INSERT INTO prescriptions')[0][1]=='Bilal','doctor stored without "Dr." (Dr. Bilal -> Bilal)')
ok(len(ins('INSERT INTO prescription_items'))==2,'2 items saved, empty row skipped')
ok(any('penicillin' in x for x in flashes(c)),'allergy warning shown after save (still saved)')

# ---- add prescription: invalid cases ----
def bad(data,label,expect):
    Cur.log.clear(); c.post('/prescriptions/add',data={**F,**base,**data})
    no_insert = not ins('INSERT INTO prescriptions')
    fl=flashes(c); ok(no_insert and any(expect in x for x in fl), label + ('' if (no_insert and any(expect in x for x in fl)) else ' ... got %r' % fl))
base={'customer_id':'1','doctor_name':'Ahmed','medicine_id[]':['1'],'dosage[]':['1 tab'],'duration[]':['3']}
bad({'customer_id':''},'no customer rejected','choose a customer')
bad({'customer_id':'99'},'unknown customer rejected','Customer not found')
bad({'doctor_name':'Dr.  '},'empty doctor name rejected','enter the doctor name')
bad({'medicine_id[]':['']},'no medicine rejected','choose a medicine')
bad({'medicine_id[]':['1'],'dosage[]':['']},'missing dosage rejected','enter the dosage')
bad({'duration[]':['0']},'0 days rejected','between 1 and 365')
bad({'duration[]':['400']},'400 days rejected','between 1 and 365')
bad({'duration[]':['abc']},'text days rejected','must be a number')
bad({'medicine_id[]':['77'],'dosage[]':['x'],'duration[]':['2']},'unknown medicine rejected','medicine not found')
bad({'medicine_id[]':['',''],'dosage[]':['',''],'duration[]':['','']},'all rows empty rejected','at least one medicine')

# ---- receipt ----
ST['dispensed']=0
h=c.get('/prescription/receipt/5').get_data(as_text=True)
ok('Dr. Bilal' in h and 'Dr. Dr.' not in h,'receipt shows "Dr. Bilal" once (no Dr. Dr.)')
ok('Dispense (make sale)' in h and 'Dispensed as sale' not in h,'receipt: Dispense button when not dispensed')
ST['dispensed']=1
h=c.get('/prescription/receipt/5').get_data(as_text=True)
ok('Dispensed as sale' in h and '#77' in h,'receipt lists the sale it was dispensed in')
ok('Dispense (make sale)' not in login('Cashier').get('/prescription/receipt/5').get_data(as_text=True),'cashier: no Dispense button')

# ---- dispense: new sale from prescription ----
ST['dispensed']=0; ST['hist']='asthma'
ST['rx_items']=[dict(medicine_id=2,dosage='1 tablet',medicine_name='Panadol',stock_quantity=50),dict(medicine_id=3,dosage='x',medicine_name='Brufen',stock_quantity=0)]
h=c.get('/sales/new?rx=5').get_data(as_text=True)
ok('name="prescription_id" value="5"' in h,'new sale from prescription carries prescription id')
ok('var PREFILL = [{"mid": 2, "qty": 1}]' in h,'Panadol prefilled; out-of-stock Brufen NOT prefilled')
ok('out of stock' in h,'warning shown for out-of-stock medicine')
ok('value="1" selected' in h,'customer of prescription pre-selected (customer 1)')
ok('Dispensing' in h and 'prescription #5' in h,'banner: Dispensing prescription #5')
h2=c.get('/sales/new?rx=999').get_data(as_text=True)
ok('Prescription not found' in h2,'unknown prescription id -> friendly message')

# ---- sale POST with prescription ----
ST['rx_fetch']=dict(prescription_id=5,customer_id=1)
Cur.log.clear()
r=c.post('/sales/new',data={**F,'payment_method':'Cash','medicine_id[]':['2'],'quantity[]':['1'],'prescription_id':'5'})
si=ins('INSERT INTO sales')
ok(r.status_code==302 and si and si[0][9]==5,'sale saved with prescription_id 5 (linked)')
Cur.log.clear(); ST['rx_fetch']=dict(prescription_id=5,customer_id=1)
r=c.post('/sales/new',data={**F,'payment_method':'Cash','medicine_id[]':['2'],'quantity[]':['1'],'customer_id':'2','prescription_id':'5'})
ok(not ins('INSERT INTO sales') and any('another customer' in x for x in flashes(c)),'prescription of another customer -> blocked')
Cur.log.clear(); ST['rx_fetch']=None
r=c.post('/sales/new',data={**F,'payment_method':'Cash','medicine_id[]':['2'],'quantity[]':['1'],'prescription_id':'888'})
ok(not ins('INSERT INTO sales') and any('Prescription not found' in x for x in flashes(c)),'missing prescription id -> blocked')
# customer taken from prescription when none chosen
Cur.log.clear(); ST['rx_fetch']=dict(prescription_id=5,customer_id=2)
c.post('/sales/new',data={**F,'payment_method':'Cash','medicine_id[]':['2'],'quantity[]':['1'],'prescription_id':'5'})
si=ins('INSERT INTO sales'); ok(si and si[0][0]==2,'no customer chosen -> customer taken from prescription')
# allergy warning on normal sale (no prescription)
ST['hist']='asthma'; Cur.log.clear(); ST['rx_fetch']=None
c.post('/sales/new',data={**F,'payment_method':'Cash','medicine_id[]':['3'],'quantity[]':['1'],'customer_id':'1'})
ok(any('asthma' in x for x in flashes(c)),'allergy warning on normal sale (asthma + Brufen)')
