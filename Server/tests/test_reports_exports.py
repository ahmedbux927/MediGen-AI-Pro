"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, types, os, re
from decimal import Decimal
from datetime import date, datetime, timedelta
ROOT=os.environ.get('ROOT',ROOT)
sys.path.insert(0,ROOT); os.chdir(ROOT)
bc=types.ModuleType('bcrypt'); bc.gensalt=lambda *a,**k:b''; bc.hashpw=lambda p,s:b'h:'+p; bc.checkpw=lambda p,h:h==b'h:'+p
sys.modules['bcrypt']=bc
D=Decimal
class Cur:
    log=[]
    def execute(self,sql,p=None): self.sql=" ".join(sql.split()); self.p=p; Cur.log.append((self.sql,p))
    def fetchone(self):
        s=self.sql
        if 'information_schema' in s: return {'n':1}
        if 'SUM(stock_quantity > 0)' in s: return {'total':2,'in_stock':1,'low':1,'empty':1,'out_count':1}
        if 'COUNT(*) AS total' in s: return {'total':2}
        return None
    def fetchall(self):
        s=self.sql
        if s.startswith('SELECT DATE(sale_date) AS sale_day'):
            return [dict(sale_day=date(2026,10,12),invoices=3,revenue=D('900.00')),dict(sale_day=date(2026,10,11),invoices=2,revenue=D('300.00'))]
        if s.startswith('SELECT m.name, si.quantity'):
            return [dict(name='Panadol',quantity=10,unit_price=D('100'),returned_qty=2,unit_cost=D('80')),
                    dict(name='Panadol',quantity=5,unit_price=D('100'),returned_qty=0,unit_cost=D('80')),
                    dict(name='Brufen',quantity=4,unit_price=D('50'),returned_qty=4,unit_cost=D('30'))]
        if s.startswith('SELECT name, stock_quantity, reorder_level FROM medicines'):
            return [dict(name='Brufen',stock_quantity=0,reorder_level=10),dict(name='Amoxicillin',stock_quantity=5,reorder_level=20)]
        if s.startswith('SELECT m.name, b.batch_number'):
            return [dict(name='Disprin',batch_number='B7',expiry_date=date(2026,11,1),quantity=9),dict(name='Old',batch_number='B1',expiry_date=date(2026,9,1),quantity=3)]
        if s.startswith('SELECT m.name, c.category_name'):
            return [dict(name='Panadol',category_name='Pain',price=D('100'),cost_price=D('80'),stock_quantity=50,reorder_level=20),
                    dict(name='Brufen',category_name=None,price=D('50'),cost_price=None,stock_quantity=0,reorder_level=10)]
        return []
    def close(self): pass
class Conn:
    def cursor(self): return Cur()
    def commit(self): pass
    def rollback(self): pass
m=types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self,app): self.connection=Conn()
m.MySQL=MySQL; sys.modules['flask_mysqldb']=m
import app as A
A.app.template_folder=ROOT+'/templates'
ok=lambda c,msg: print(('PASS ' if c else 'FAIL ')+msg)
def login(role='Admin'):
    c=A.app.test_client(); c.get('/login')
    with c.session_transaction() as s: s.update(user_id=1,user_name='Ahmed',role=role); s['_csrf']='t'
    return c
c=login('Admin')
for tab in ['overview','sales','profit','stock','expiry']:
    r=c.get(f'/reports?tab={tab}&start_date=2026-10-01&end_date=2026-10-12')
    h=r.get_data(as_text=True)
    ok(r.status_code==200 and 'Reports' in h,f'reports tab "{tab}" renders')
h=c.get('/reports?tab=profit&start_date=2026-10-01&end_date=2026-10-12').get_data(as_text=True)
ok('Rs. 160' in h,'profit total = net revenue 1,200 - cost 1,040 = Rs. 160')
ok('Panadol' in h and 'Brufen' not in h.split('Profit')[0] or 'Brufen' in h,'profit tab lists medicines')
ok('/audit' not in c.get('/reports').get_data(as_text=True), 'reports page has no Audit link (feature removed)')
h=c.get('/reports?start_date=garbage&end_date=2026-10-01&tab=nonsense').get_data(as_text=True)
ok('Reports' in h,'bad dates / bad tab fall back safely')
h=c.get('/reports?start_date=2026-10-12&end_date=2026-10-01').get_data(as_text=True)
ok('Reports' in h,'reversed dates are swapped, no crash')
r=c.get('/reports/export/sales?start_date=2026-10-01&end_date=2026-10-12')
ok(r.status_code==200 and r.mimetype=='text/csv' and 'attachment' in r.headers['Content-Disposition'] and 'Invoices' in r.get_data(as_text=True),'sales CSV download works')
r=c.get('/reports/export/profit?start_date=2026-10-01&end_date=2026-10-12'); csvt=r.get_data(as_text=True)
ok('Panadol' in csvt and 'Cost (Rs.)' in csvt,'profit CSV has medicines and cost column')
ok(c.get('/reports/export/stock').status_code==200 and c.get('/reports/export/expiry').status_code==200,'stock and expiry CSV work')
ok(c.get('/reports/export/bogus').status_code==302,'unknown export type -> safe redirect')
ok(login('Pharmacist').get('/reports').status_code==302,'Pharmacist cannot open reports')
ok(login('Pharmacist').get('/reports/export/sales').status_code==302,'Pharmacist cannot export reports')
r=c.get('/medicines/export'); t=r.get_data(as_text=True)
ok(r.status_code==200 and r.mimetype=='text/csv' and 'Medicine,Category' in t and 'Out of stock' in t,'medicine export CSV (all)')
ok(c.get('/medicines/export?ids=1,2').status_code==200,'medicine export with selected ids')
Cur.log.clear(); c.get('/medicines/export?ids=1,x,2'); ok(any('IN (%s,%s)' in q for q,_ in Cur.log),'selected ids: only numbers used, IN list built')
ok(login('Cashier').get('/medicines/export').status_code==302,'Cashier cannot export medicines')
ok(c.get('/medicines').status_code==200,'medicines page still renders (export link resolves)')
