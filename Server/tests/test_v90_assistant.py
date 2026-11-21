"""v92.00: AI assistant - medicine knowledge base, natural how-to matching,
software questions, visible theme, remember-me confirmation.
Source-level checks + engine behaviour with a mock cursor (no MySQL)."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from decimal import Decimal as D

passed = failed = 0
def ok(cond, label):
    global passed, failed
    if cond:
        passed += 1
        print('PASS', label)
    else:
        failed += 1
        print('FAIL:', label)

from config import Config
ok(Config.APP_VERSION == '101.03', 'version is 100.00 (one source)')

# ---- knowledge base file ----
import medicine_knowledge as mk
ok(len(mk.MEDICINES) >= 100, f'knowledge base has 100+ medicines ({len(mk.MEDICINES)})')
for q, want in [('What is Paracetamol used for?', 'Paracetamol'),
                ('Brufen kis liye use hoti hai?', 'Ibuprofen'),
                ('Augmentin side effects', 'Co-Amoxiclav'),
                ('Flagyl ke fayde', 'Metronidazole'),
                ('Lasix kya hai', 'Furosemide'),
                ('What is Cetirizine?', 'Cetirizine'),
                ('Risek uses', 'Omeprazole'),
                ('Tell me about insulin', 'Insulin'),
                ('Glucophage side effects', 'Metformin'),
                ('Viagra warnings', 'Sildenafil')]:
    e = mk.find_medicine(q)
    ok(e is not None and e['name'] == want, f'KB lookup: {q!r} -> {want}')
ok(mk.find_medicine('What is the weather today?') is None, 'KB does not invent answers for non-medicines')
ans = mk.format_answer(mk.find_medicine('What is Paracetamol used for?'))
ok('Used for:' in ans and 'side effects' in ans.lower() and 'General information only' in ans,
   'KB answer has uses, side effects and the safety note')

# ---- engine behaviour (mock cursor, same pattern as test_chatbot_basic) ----
import chatbot_engine as ce
MEDS = [dict(medicine_id=1, name='Panadol', price=D('100'), stock_quantity=892, reorder_level=50, category_name='Pain'),
        dict(medicine_id=2, name='Brufen', price=D('50'), stock_quantity=0, reorder_level=10, category_name='Pain')]

class Cur:
    def execute(self, sql, p=None):
        self.sql = " ".join(sql.split())
    def fetchone(self):
        return None
    def fetchall(self):
        s = self.sql
        if 'FROM medicines m LEFT JOIN categories' in s: return MEDS
        return []
    def close(self): pass

USER = {'name': 'Ahmed', 'role': 'Admin'}

def ask(q):
    a, chips = ce.get_answer(Cur(), q, USER, {})
    return a

a = ask('How do I take a backup?')
ok('backup' in a.lower() and 'did not understand' not in a, 'natural backup question gets the guide')
a = ask('backup')
ok('backup' in a.lower() and 'did not understand' not in a, 'single word "backup" gets the guide')
a = ask('What is Paracetamol used for?')
ok('Used for:' in a and 'fever' in a.lower(), 'paracetamol uses answered from knowledge base')
ok('In your shop' in a, 'KB answer adds the shop stock line (Panadol is paracetamol)')
a = ask('Brufen kis liye use hoti hai?')
ok('Ibuprofen' in a and 'Used for:' in a, 'Roman Urdu medicine question answered (Brufen = Ibuprofen)')
a = ask('What is Cetirizine?')
ok('Used for:' in a and 'not in your shop catalog' in a, 'medicine not stocked still gets a knowledge answer')
a = ask('What can this software do?')
ok('MediGen AI Pro' in a and 'Sales' in a, 'software question answered with the program overview')
a = ask('What are the features of this program?')
ok('MediGen AI Pro' in a, 'program features question answered')
a = ask('Panadol stock')
ok('did not understand' not in a and 'knowledge' not in a.lower(), 'plain stock question keeps stock behaviour')
a = ask('Panadol price')
ok('Rs.' in a, 'plain price question keeps price behaviour')
a = ask('How to add medicine')
ok('Add Medicine' in a, 'classic how-to still works')

# ---- theme + remember-me visibility (source checks) ----
base = open(os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
login = open(os.path.join(ROOT, 'templates', 'login.html'), encoding='utf-8').read()
ok('css/app.css' in base and '===== v92-theme.css =====' in open(os.path.join(ROOT, 'static', 'css', 'app.css'), encoding='utf-8').read() and 'v92-theme.css' in login, 'v90 theme loaded on app pages (bundle) and login')
css = open(os.path.join(ROOT, 'static', 'css', 'v92-theme.css'), encoding='utf-8').read()
ok('linear-gradient' in css and '.sidebar' in css, 'v90 theme has the gradient sidebar')
auth = open(os.path.join(ROOT, 'pharmacy', 'routes', 'auth.py'), encoding='utf-8').read()
ok('Remember me is ON' in auth, 'login confirms remember-me to the user')

print(f'done: {passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
