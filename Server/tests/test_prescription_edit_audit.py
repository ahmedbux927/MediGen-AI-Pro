"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, types, os, re
from decimal import Decimal
from datetime import datetime
sys.path.insert(0,ROOT); os.chdir(ROOT)
bc=types.ModuleType('bcrypt'); bc.gensalt=lambda *a,**k:b''; bc.hashpw=lambda p,s:b'h:'+p; bc.checkpw=lambda p,h:h==b'h:'+p
sys.modules['bcrypt']=bc
ST={'dispensed':0,'exists':True}
MEDS={1:'Amoxicillin',2:'Panadol'}
class Cur:
    log=[]; lastrowid=77
    def execute(self,sql,p=None):
        self.sql=" ".join(sql.split()); self.p=p; Cur.log.append((self.sql,p))
    def fetchone(self):
        s=self.sql; p=self.p
        if s.startswith('SELECT COUNT(*) AS today'): return {'today':2,'failed_logins':0,'deletes':0,'denied':0,'users':1}
        if 'information_schema' in s: return {'n':1}
        if s.startswith('SELECT customer_id, medical_history FROM customers'):
            return dict(customer_id=int(p[0]),medical_history='allergic to penicillin') if p[0]=='1' else None
        if s.startswith('SELECT name FROM medicines WHERE medicine_id'):
            return {'name':MEDS[int(p[0])]} if int(p[0]) in MEDS else None
        if s.startswith('SELECT COUNT(*) AS n FROM sales WHERE prescription_id'): return {'n':ST['dispensed']}
        if s.startswith('SELECT p.*, c.name AS customer_name, c.medical_history'):
            return dict(prescription_id=5,customer_id=1,doctor_name='Dr. Ahmed',date_issued=datetime(2026,10,13).date(),notes='rest',customer_name='Ali',medical_history='asthma') if ST['exists'] else None
        if s.startswith('SELECT p.doctor_name, c.name AS customer_name'):
            return dict(doctor_name='Dr. Ahmed',customer_name='Ali') if ST['exists'] else None
        if s.startswith('SELECT COUNT(*) AS total FROM audit_log'): return {'total':2}
        if s.startswith('SELECT COUNT(*) AS total FROM prescriptions') or 'AS total FROM prescriptions p JOIN' in s: return {'total':30}
        if 'SUM((SELECT COUNT' in s: return {'total':30,'dispensed':Decimal(12)}
        return None
    def fetchall(self):
        s=self.sql
        if s.startswith('SELECT p.*, c.name AS customer_name, (SELECT'):
            return [dict(prescription_id=5,date_issued=datetime(2026,10,13).date(),customer_name='Ali',doctor_name='Dr. Ahmed',item_count=1,dispensed_count=0,sale_id=None),
                    dict(prescription_id=4,date_issued=datetime(2026,10,12).date(),customer_name='Sara',doctor_name='Bilal',item_count=1,dispensed_count=1,sale_id=77)]
        if s.startswith('SELECT sale_id FROM sales WHERE prescription_id'):
            return [{'sale_id':37}] if ST['dispensed'] else []
        if s.startswith('SELECT pi.medicine_id, pi.dosage, pi.duration_days'):
            return [dict(medicine_id=1,dosage='1 tablet twice a day',duration_days=5)]
        if s.startswith('SELECT medicine_id, name FROM medicines'):
            return [dict(medicine_id=1,name='Amoxicillin'),dict(medicine_id=2,name='Panadol')]
        if s.startswith('SELECT * FROM audit_log'):
            return [dict(audit_id=2,created_at=datetime(2026,10,13,9,0),username='Ahmed',ip='127.0.0.1',action='prescription.edit',entity='prescription',entity_id=5,details='Ahmed, 1 medicine(s)'),
                    dict(audit_id=1,created_at=datetime(2026,10,13,8,0),username='Ahmed',ip='127.0.0.1',action='sale.create',entity='sale',entity_id=3,details='Total 300.00')]
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
def flashes(c):
    with c.session_transaction() as s: return [m for _,m in s.get('_flashes',[])]
def sqls(prefix): return [(x,p) for x,p in Cur.log if x.startswith(prefix)]
F={'csrf_token':'t'}
c=login('Admin')

# ---- list buttons ----
h=c.get('/prescriptions').get_data(as_text=True)
ok('ibtn print' in h and 'ibtn edit' in h and 'ibtn del' in h,'list: Print, Edit and Delete buttons in one column (Admin)')
ok('data-method="post"' in h and 'Delete prescription #5' in h,'list: delete is a POST link with confirm')
ok('Dr. Ahmed' in h and 'Dr. Dr.' not in h and 'Dr. Bilal' in h and 'rxp-stat' in h,'list: doctor names shown once as "Dr. X" (stored "Dr. Ahmed" and "Bilal")')
ph=login('Pharmacist').get('/prescriptions').get_data(as_text=True)
ok('ibtn print' in ph and 'ibtn edit' in ph and 'ibtn del' not in ph,'Pharmacist: Print + Edit, no Delete button')
ok(login('Cashier').get('/prescriptions').status_code==302,'Cashier cannot open prescriptions')

# ---- edit page (GET) ----
Cur.log.clear(); ST['dispensed']=0
h=c.get('/prescriptions/5/edit').get_data(as_text=True)
ok('value="Ahmed"' in h,'edit: doctor field shows "Ahmed" (no Dr. in the input)')
ok('Amoxicillin' in h and 'selected' in h and 'value="1 tablet twice a day"' in h,'edit: existing medicine, dosage and days loaded')
ok('This prescription was already dispensed' not in h,'edit: not dispensed -> medicines editable')
ST['dispensed']=1
h=c.get('/prescriptions/5/edit').get_data(as_text=True)
ok('already dispensed in sale' in h and '#37' in h and 'disabled' not in h and 'Add medicine' in h,'edit: dispensed -> notice shown, medicines still editable')

# ---- edit POST (not dispensed) ----
ST['dispensed']=0; Cur.log.clear()
r=c.post('/prescriptions/5/edit',data={**F,'doctor_name':'Dr. Bilal','notes':'new note',
     'medicine_id[]':['1','2'],'dosage[]':['1 tab','2 tabs'],'duration[]':['4','6']})
ok(r.status_code==302,'edit saved, redirected to list')
ok(sqls('UPDATE prescriptions SET doctor_name')[0][1][0]=='Bilal','edit: doctor "Dr. Bilal" saved as "Bilal"')
ok(len(sqls('DELETE FROM prescription_items'))==1 and len(sqls('INSERT INTO prescription_items'))==2,'edit: old medicines replaced by the 2 new rows')
ok(any(p and p[2]=='prescription.edit' for x,p in sqls('INSERT INTO audit_log')),'edit written to audit log (prescription.edit)')

# ---- edit POST validation ----
Cur.log.clear()
c.post('/prescriptions/5/edit',data={**F,'doctor_name':'Ahmed','medicine_id[]':['1'],'dosage[]':['x'],'duration[]':['0']})
ok(not sqls('UPDATE prescriptions') and any('between 1 and 365' in x for x in flashes(c)),'edit: invalid days -> nothing saved, message shown')
Cur.log.clear()
c.post('/prescriptions/5/edit',data={**F,'doctor_name':'  ','medicine_id[]':['1'],'dosage[]':['x'],'duration[]':['2']})
ok(not sqls('UPDATE prescriptions') and any('enter the doctor name' in x for x in flashes(c)),'edit: empty doctor name -> rejected')

# ---- edit POST (dispensed): medicines untouched ----
ST['dispensed']=1; Cur.log.clear()
c.post('/prescriptions/5/edit',data={**F,'doctor_name':'Dr. Sami','notes':'x','medicine_id[]':['2'],'dosage[]':['changed'],'duration[]':['9']})
ok(sqls('UPDATE prescriptions SET doctor_name')[0][1][0]=='Sami' and len(sqls('INSERT INTO prescription_items'))==1,'dispensed: medicines can be changed now')
ok(any(p and 'NOT changed' in str(p) for x,p in sqls('INSERT INTO audit_log')),'dispensed edit: audit says the sale was NOT changed')

# ---- delete ----
ST['dispensed']=0; Cur.log.clear()
r=c.post('/prescriptions/5/delete',data=F)
ok(r.status_code==302 and sqls('DELETE FROM prescriptions') and any(p and p[2]=='prescription.delete' for x,p in sqls('INSERT INTO audit_log')),'delete: removed and written to audit log')
Cur.log.clear(); ST['dispensed']=1
c.post('/prescriptions/5/delete',data=F)
ok(not sqls('DELETE FROM prescriptions') and any('cannot be deleted' in x for x in flashes(c)),'delete: dispensed prescription is protected')
Cur.log.clear(); c.post('/prescriptions/5/delete',data={})
ok(not sqls('DELETE FROM prescriptions'),'delete without CSRF token -> nothing deleted')
ok(c.get('/prescriptions/5/delete').status_code==405,'delete by GET link -> 405 (not allowed)')
Cur.log.clear(); ST['dispensed']=0
login('Pharmacist').post('/prescriptions/5/delete',data={**F})
ok(not sqls('DELETE FROM prescriptions'),'Pharmacist cannot delete')
ST['exists']=False; Cur.log.clear(); c.post('/prescriptions/99/delete',data=F); ok(not sqls('DELETE FROM prescriptions') and any('not found' in x for x in flashes(c)),'delete unknown id -> not found message'); ST['exists']=True

# ---- add writes audit ----
Cur.log.clear()
c.post('/prescriptions/add',data={**F,'customer_id':'1','doctor_name':'Dr. Kamran','medicine_id[]':['2'],'dosage[]':['1 tab'],'duration[]':['3']})
ok(any(p and p[2]=='prescription.add' for x,p in sqls('INSERT INTO audit_log')),'add: written to audit log')

# ---- audit page ----
ok(c.get('/audit').status_code == 404, 'audit page is removed (404)')
ok('Audit Log' not in c.get('/prescriptions').get_data(as_text=True),'Admin does not see Audit Log in the menu (removed)')
