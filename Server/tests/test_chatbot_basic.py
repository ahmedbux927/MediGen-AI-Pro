"""Basic chatbot questions: every question must give a text answer and never crash."""
import os as _os, sys as _sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
from decimal import Decimal as D
import chatbot_engine as ce

MEDS = [dict(medicine_id=1, name='Panadol', price=D('100'), stock_quantity=892, reorder_level=50, category_name='Pain'),
        dict(medicine_id=2, name='Brufen', price=D('50'), stock_quantity=0, reorder_level=10, category_name='Pain')]

class Cur:
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split())
    def fetchone(self):
        s = self.sql
        if 'GROUP BY m.name' in s and 'LIMIT 1' in s: return {'name': 'Panadol', 'sold': 5}
        if 'AS c, IFNULL' in s or 'AS c, ' in s: return {'c': 3, 't': D('1200')}
        if 'COUNT(*) AS c' in s and 'FROM customers' in s: return {'c': 7}
        if 'COUNT(*) AS c' in s and 'FROM medicines' in s: return {'c': 2}
        if 'COUNT(*) AS c' in s: return {'c': 7}
        if 'SUM(CASE' in s: return {'total': 2, 'out_count': 1, 'low': 1}
        if 'SUM(si.quantity)' in s or 'SUM(quantity)' in s: return {'s': 12}
        if 'price * stock' in s: return {'v': 9999}
        if 'AS net_revenue' in s: return {'net_revenue': D('1200')}
        if 'GROUP BY m.name' in s and 'LIMIT 1' in s: return {'name': 'Panadol', 'sold': 5}
        return None      # like a real database: no row found
    def fetchall(self):
        s = self.sql
        if 'FROM medicines m LEFT JOIN categories' in s: return MEDS
        if 'stock_quantity <= 0' in s: return [dict(name='Brufen')]
        if 'stock_quantity <= reorder_level' in s: return [dict(name='Brufen', stock_quantity=0, reorder_level=10)]
        if 'b.expiry_date' in s: return []
        if 'GROUP BY m.name' in s: return [dict(name='Panadol', sold=40, revenue=D('4000'))]
        return []
    def close(self): pass

QUESTIONS = ['Hello', 'Panadol stock?', 'panadoll ka stock kitna hai', 'Brufen price', 'Today sales?', 'this week revenue',
             'yesterday sales', 'Low stock medicines?', 'out of stock', 'Expiring soon?', 'Top selling medicines',
             'Total customers?', 'How many medicines', 'How to add medicine', 'how to make a sale', 'help', 'what is the date today',
             'xyzabc gibberish', 'thanks', 'bye']
ok_count = 0
for q in QUESTIONS:
    try:
        ans, chips = ce.get_answer(Cur(), q, {'name': 'Ahmed', 'role': 'Admin'}, {})
        good = isinstance(ans, str) and len(ans) > 0 and isinstance(chips, list)
    except Exception as e:
        good = False
        print('     error on', repr(q), e)
    if good:
        ok_count += 1
        print(f'PASS answered: {q!r}')
    else:
        print(f'FAIL no answer: {q!r}')
