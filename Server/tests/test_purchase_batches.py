"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, types, os, re, json
from decimal import Decimal
from datetime import date, timedelta
sys.path.insert(0,ROOT); os.chdir(ROOT)
bc=types.ModuleType('bcrypt'); bc.gensalt=lambda *a,**k:b''; bc.hashpw=lambda p,s:b'h:'+p; bc.checkpw=lambda p,h:h==b'h:'+p
sys.modules['bcrypt']=bc
TODAY=date.today()
ST={'existing':None,'batches':[dict(batch_id=1,quantity=20),dict(batch_id=2,quantity=100)],'mismatch':[]}
class Cur:
    log=[]; lastrowid=55
    def execute(self,sql,p=None): self.sql=" ".join(sql.split()); Cur.log.append((self.sql,p))
    def fetchone(self):
        s=self.sql
        if 'information_schema' in s: return {'n':1}
        if 'FROM batches WHERE medicine_id=%s AND batch_number=%s' in s: return ST['existing']
        if s.startswith('SELECT COUNT(*) AS total'): return {'total':60}
        if 'AS active_batches' in s: return dict(active_batches=Decimal(5),expired_batches=Decimal(2),expired_units=Decimal(300),expired_value=Decimal('12000.00'),soon_batches=Decimal(1))
        if 'SELECT COUNT(*) AS n FROM (' in s: return {'n':3}
        if 'FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id WHERE b.batch_id' in s:
            return ST.get('wo')
        return None
    def fetchall(self):
        s=self.sql
        if s.startswith('SELECT b.*, m.name AS medicine_name'):
            mk=lambda i,st,dl,q: dict(batch_id=i,medicine_name=f'M{i}',batch_number=f'B{i}',expiry_date=TODAY+timedelta(days=dl),days_left=dl,quantity=q,status=st)
            return [mk(1,'expired',-30,10),mk(2,'soon',20,5),mk(3,'ok',400,50),mk(4,'empty',100,0)]
        if 'FROM suppliers' in s: return [dict(supplier_id=1,name='Arslan')]
        if 'SELECT medicine_id, name FROM medicines' in s: return [dict(medicine_id=1,name='Panadol')]
        if 'GROUP BY m.medicine_id, m.name, m.stock_quantity, m.cost_price' in s: return ST['mismatch']
        if 'FROM batches WHERE medicine_id=%s AND quantity > 0' in s: return ST['batches']
        if 'FROM purchase_items pi JOIN medicines' in s: return [dict(name='Panadol',batch_number='B1',expiry_date=TODAY,quantity=10,unit_price=Decimal('5.00'))]
        if 'FROM purchase_orders po' in s: return [dict(po_id=9,supplier_name='Arslan',order_date=TODAY,delivery_date=TODAY,total_amount=Decimal(50),status='Received')]
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
c=login(); F={'csrf_token':'t'}
fut=(TODAY+timedelta(days=200)).isoformat(); past=(TODAY-timedelta(days=1)).isoformat()
def purchase(**kw):
    d={**F,'supplier_id':'1','medicine_id[]':['1','1',''],'quantity[]':['10','5',''],'unit_price[]':['6.5','7',''],
       'batch_number[]':['AB-1','','' ],'expiry_date[]':[fut,fut,'']}
    d.update(kw); Cur.log.clear(); ST['existing']=kw.get('_existing')
    d.pop('_existing',None)
    return c.post('/purchase/new',data=d)

r=purchase()
q=[x for x,_ in Cur.log]
ok(r.status_code==302,'purchase saved')
ok(sum(1 for x in q if x.startswith('INSERT INTO purchase_items'))==2,'2 items inserted, empty 3rd row skipped')
ins=[p for x,p in Cur.log if x.startswith('INSERT INTO purchase_items')]
ok(ins[0][2]=='AB-1' and ins[1][2]=='B55-1','given batch no kept; blank batch no -> auto "B55-1"')
ok(sum(1 for x in q if x.startswith('INSERT INTO batches'))==2,'batches created for each item')
ok(any(x.startswith('UPDATE medicines SET cost_price') for x in q),'medicine cost price updated')
ok(any('delivery_date' in x and x.startswith('INSERT INTO purchase_orders') for x in q),'delivery date set')

purchase(**{'expiry_date[]':[past,fut,'']}); ok(not any(x.startswith('INSERT INTO purchase_orders') for x,_ in Cur.log),'past expiry date rejected')
purchase(**{'expiry_date[]':['',fut,'']}); ok(not any(x.startswith('INSERT INTO purchase_orders') for x,_ in Cur.log),'missing expiry date rejected')
purchase(**{'quantity[]':['0','5','']}); ok(not any(x.startswith('INSERT INTO purchase_orders') for x,_ in Cur.log),'quantity 0 rejected')
purchase(**{'medicine_id[]':['','',''],'quantity[]':['','','']}); ok(not any(x.startswith('INSERT INTO purchase_orders') for x,_ in Cur.log),'empty purchase rejected')

# existing batch with same expiry -> quantity added
ex={'batch_id':9,'expiry_date':TODAY+timedelta(days=200)}
purchase(_existing=ex); ups=[(x,p) for x,p in Cur.log if x.startswith('UPDATE batches SET quantity = quantity +')]
ok(len(ups)==2,'same batch number + same expiry -> quantity merged (no duplicate batch)')
# existing batch, different expiry -> conflict, rollback, nothing committed
Conn.rb=0; ex2={'batch_id':9,'expiry_date':TODAY+timedelta(days=50)}
r=purchase(_existing=ex2); ok(Conn.rb>=1,'same batch number + different expiry -> rolled back')
fl=[mm for _,mm in c.session_transaction().__enter__().get('_flashes',[])]
ok(any('different expiry' in x or 'already exists' in x for x in fl),'  ...with a clear message')

h=c.get('/purchase/new').get_data(as_text=True)
ok('name="expiry_date[]"' in h and 'name="batch_number[]"' in h and 'min="%s"'%(TODAY+timedelta(days=1)).isoformat() in h,'purchase form has batch + expiry fields (min = tomorrow)')
ok(c.get('/purchase/9/items').json[0]['batch']=='B1','purchase items JSON')
h=c.get('/purchase').get_data(as_text=True); ok('showItems' in h and '#' not in 'x' and '>9<' in h,'purchase list shows PO id + View button')

# batches page
Cur.log.clear(); h=c.get('/batches?filter=expired&q=pan').get_data(as_text=True)
sq=' '.join(x for x,_ in Cur.log)
ok("b.expiry_date < CURDATE()" in sq and 'm.name LIKE' in sq,'expired filter + search in SQL')
ok('EXPIRED' in h and 'EXPIRING SOON' in h and 'SOLD OUT' in h and 'Write off' in h,'status badges + write-off button')
ok('Rs. 12,000' in h and '300 units' in h,'expired stock value card')
ok('3</strong> medicine(s) have a stock quantity' in h,'mismatch warning shown to Admin')
h2=login('Pharmacist').get('/batches').get_data(as_text=True); ok('Fix now' not in h2 and 'Sync batches' not in h2,'Pharmacist does not see sync tools')

# write-off
Cur.log.clear(); ST['wo']=dict(batch_id=2,medicine_id=1,batch_number='X',expiry_date=TODAY-timedelta(days=5),quantity=40,name='Panadol',stock_quantity=100)
c.post('/batches/writeoff/2',data=F)
ok(any(x.startswith('UPDATE batches SET quantity = 0') for x,_ in Cur.log) and any(p and p[0]==60 for x,p in Cur.log if x.startswith('UPDATE medicines SET stock_quantity')),'write-off: batch -> 0, stock 100 -> 60')
ok(any("'Expired'" in x and p[2]==-40 for x,p in Cur.log if x.startswith('INSERT INTO stock_adjustments')),'write-off logged in stock history (-40)')
Cur.log.clear(); ST['wo']=dict(batch_id=2,medicine_id=1,batch_number='X',expiry_date=TODAY+timedelta(days=5),quantity=40,name='Panadol',stock_quantity=100)
c.post('/batches/writeoff/2',data=F); ok(not any(x.startswith('UPDATE batches') for x,_ in Cur.log),'cannot write off a batch that is not expired')

# reconcile
ST['mismatch']=[dict(medicine_id=1,name='Panadol',stock=892,batch_qty=500,cost=Decimal('80'),diff=0),dict(medicine_id=2,name='Paracetamol',stock=1,batch_qty=300,cost=Decimal('40'),diff=0)]
h=c.get('/batches/reconcile').get_data(as_text=True); ok('add opening batch of 392' in h and 'remove 299 from batches' in h,'reconcile preview shows +392 / -299')
Cur.log.clear(); ST['existing']=None; ST['batches']=[dict(batch_id=7,quantity=200),dict(batch_id=8,quantity=100)]
c.post('/batches/reconcile',data={**F,'default_expiry':fut})
ins=[p for x,p in Cur.log if x.startswith('INSERT INTO batches')]
ok(len(ins)==1 and ins[0][1]=='OPENING-1' and ins[0][3]==392,'opening batch created for missing 392 units')
trim=[p for x,p in Cur.log if x.startswith('UPDATE batches SET quantity = quantity - ')]
ok(trim==[(200,7),(99,8)],f'extra 299 removed oldest first: {trim}')
Cur.log.clear(); c.post('/batches/reconcile',data={**F,'default_expiry':past}); ok(not any(x.startswith('INSERT INTO batches') for x,_ in Cur.log),'past expiry for reconcile rejected')
ok(login('Pharmacist').post('/batches/reconcile',data={**F,'default_expiry':fut}).status_code==302,'reconcile is Admin-only')
