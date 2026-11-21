"""Auto-run mock suite. Runs without MySQL. Project root is found from this file's location."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))

import sys, os
from decimal import Decimal as D
from datetime import date, datetime, timedelta
sys.path.insert(0,ROOT); os.chdir(ROOT)
import chatbot_engine as ce
TODAY=date.today()
MEDS=[dict(medicine_id=1,name='Amoxicillin',price=D('100'),stock_quantity=5,reorder_level=20,category_name='Antibiotic'),
      dict(medicine_id=2,name='Brufen',price=D('50'),stock_quantity=0,reorder_level=10,category_name='Pain'),
      dict(medicine_id=3,name='Panadol',price=D('100'),stock_quantity=120,reorder_level=50,category_name='Pain')]
class Cur:
    def execute(self,sql,p=None):
        self.sql=" ".join(sql.split()); self.p=p
    def fetchone(self):
        s=self.sql
        if 'AS net_revenue FROM sales' in s: return {'net_revenue':D('1200')}
        if 'AS n, IFNULL(SUM(refund_amount)' in s: return {'n':2,'v':D('300')}
        if 'FROM customers WHERE LOWER(name) LIKE' in s:
            t=self.p[0].strip('%')
            if t=='ali': return {'customer_id':1,'name':'Ali Khan','contact_number':'0300','medical_history':'allergic to penicillin'}
            return None
        if 'AS c, IFNULL' in s: return {'c':0,'t':0}
        if 'COUNT(*) AS c FROM medicines WHERE stock_quantity <= reorder_level' in s: return {'c':2}
        return None
    def fetchall(self):
        s=self.sql
        if s.startswith('SELECT m.medicine_id, m.name') or 'FROM medicines m LEFT JOIN categories' in s: return MEDS
        if 'COALESCE(b.purchase_price, m.cost_price, 0) AS unit_cost' in s:
            return [dict(quantity=10,unit_price=D('100'),returned_qty=2,unit_cost=D('80')),
                    dict(quantity=5,unit_price=D('100'),returned_qty=0,unit_cost=D('80'))]
        if 'FROM sale_return_items ri' in s: return [dict(name='Panadol',q=3)]
        if 'AS due_amount FROM sales WHERE customer_id' in s:
            return [dict(sale_id=7,sale_date=datetime(2026,10,12),due_amount=D('700'))]
        if 'GROUP BY c.customer_id, c.name' in s:
            return [dict(name='Ali Khan',due_amount=D('700')),dict(name='Sara',due_amount=D('300'))]
        if s.startswith('SELECT s.name, s.contact'):
            return [dict(name='Arslan Traders',contact='03261489',orders=2,last_order=date(2026,10,3))]
        if 'FROM medicines WHERE stock_quantity <= reorder_level' in s:
            return [dict(medicine_id=1,name='Amoxicillin',stock_quantity=5,reorder_level=20),
                    dict(medicine_id=2,name='Brufen',stock_quantity=0,reorder_level=10)]
        if 'GROUP BY si.medicine_id' in s: return [dict(medicine_id=1,q=60)]
        if 'AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 60 DAY)' in s:
            return [dict(name='Disprin',batch_number='B7',expiry_date=TODAY+timedelta(days=20),quantity=9)]
        return []
    def close(self): pass
ok=lambda c,msg: print(('PASS ' if c else 'FAIL ')+msg)
ADMIN={'name':'Ahmed','role':'Admin'}; CASH={'name':'Sara','role':'Cashier'}; PHARM={'name':'Umair','role':'Pharmacist'}
def ask(q,u=ADMIN):
    a,_=ce.get_answer(Cur(),q,u,{}); return a

a=ask('Today profit'); ok('Profit (today)' in a and 'Rs. 160' in a and '13.3%' in a,'profit: net 1200 - cost 1040 = 160, margin 13.3%')
ok('only available for Admin' in ask('Today profit',PHARM),'profit: Pharmacist blocked')
ok('only available for Admin' in ask('profit this month',CASH),'profit: Cashier blocked')
a=ask('Returns this week'); ok('Value refunded: Rs. 300' in a and 'Returns: 2' in a and 'Panadol (3)' in a,'returns this week: count, value, most returned')
a=ask('Ali balance'); ok('Ali Khan: pending balance Rs. 700' in a and 'Sale #7' in a,'customer udhaar: balance and sale list')
a=ask('Udhaar list'); ok('Ali Khan: Rs. 700' in a and 'Sara: Rs. 300' in a and 'Rs. 1,000' in a,'udhaar overview: top debtors and total')
a=ask('Supplier list'); ok('Arslan Traders' in a and '2 order(s)' in a,'supplier list for Admin')
ok('only available for Admin and Pharmacist' in ask('Supplier list',CASH),'supplier list blocked for Cashier')
a=ask('What should I order?'); ok('Amoxicillin' in a and 'Suggested order: 55' in a and 'OUT of stock' in a and 'Suggested order: 20' in a,'reorder: 30-day target (55 for Amoxicillin), out-of-stock Brufen (20)')
ok('only available for Admin and Pharmacist' in ask('reorder suggestions',CASH),'reorder blocked for Cashier')
ok(ask('what should I order').startswith('**Reorder suggestions**'),'reorder answer header ok')
a=ask('Expiry discount ideas'); ok('Disprin' in a and '20 day(s) left' in a and '20-30% offer' in a and 'not medical' not in a.lower(),'expiry tips: Disprin 20 days -> strong offer advice')
a=ask('allergy check Ali'); ok('Patient: Ali Khan' in a and 'allergic to penicillin' in a and 'not medical advice' in a,'allergy check with patient history')
a=ask('Ali allergy Amoxicillin'); ok("History mentions 'penicillin'" in a and 'Amoxicillin may not be suitable' in a,'allergy: penicillin history vs Amoxicillin warning')
a=ask('allergy check Zed'); ok('patient name' in a,'allergy: unknown patient -> asks for the name')
a=ask('help'); ok('More things I can do' in a and 'Reorder' in a,'help lists the new Pro commands')
a=ask('Panadol stock'); ok('Panadol' in a and 'Stock' in a,'existing: medicine stock still works')
a=ask('Low stock'); ok('Amoxicillin' in a or 'Low stock' in a,'existing: low stock still works')
print('done')
