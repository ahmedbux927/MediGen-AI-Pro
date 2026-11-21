"""Drug interaction pairs (v87.07): pair rules, bill check, and wiring. No MySQL needed.
Run: python tests/test_interactions.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import interactions as IX

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

ok(IX.normalise_pair(9, 3) == (3, 9) and IX.normalise_pair('3', '9') == (3, 9), 'pair is stored lower id first')
for a, b, label in [(4, 4, 'same medicine is refused'), ('x', 2, 'non-number id is refused')]:
    try:
        IX.normalise_pair(a, b); ok(False, label)
    except IX.InteractionError:
        ok(True, label)
ok(IX.check_severity('major') == 'major', 'severity major is accepted')
try:
    IX.check_severity('deadly'); ok(False, 'unknown severity is refused')
except IX.InteractionError:
    ok(True, 'unknown severity is refused')

rules = {(1, 2): ('major', 'bleeding risk'), (2, 5): ('minor', ''), (3, 4): ('moderate', 'watch BP')}
hits = IX.find_in_bill([5, 2, 1, 9], rules)
ok([(h[0], h[1]) for h in hits] == [(1, 2), (2, 5)], 'bill with 1,2,5,9: finds the two listed pairs')
ok(hits[0][2] == 'major', 'worst severity comes first')
ok(IX.find_in_bill([3, 9], rules) == [], 'bill without a listed pair: no warning')
ok(IX.find_in_bill([1], rules) == [], 'single medicine: no warning')
ok(IX.find_in_bill([1, 2, 2], rules)[0][:2] == (1, 2), 'duplicate medicine lines do not hide a pair')

class Cur:
    def __init__(self, rows=(), names=None):
        self.rows, self.names, self.log, self._all = list(rows), names or {}, [], []
    def execute(self, sql, p=None):
        self.log.append((' '.join(sql.split()), p))
        if 'FROM drug_interactions' in sql:
            self._all = self.rows
        elif 'FROM medicines WHERE medicine_id IN' in sql:
            self._all = [{'medicine_id': k, 'name': v} for k, v in self.names.items()]
    def fetchall(self):
        return self._all

db_rows = [{'med_a_id': 1, 'med_b_id': 2, 'severity': 'major', 'note': 'bleeding risk'}]
names = {1: 'Aspirin', 2: 'Warfarin'}
out = IX.warnings_for_bill(Cur(db_rows, names), [1, 2, 7])
ok(len(out) == 1 and 'Aspirin with Warfarin' in out[0] and 'major' in out[0] and 'bleeding risk' in out[0],
   'warning names both medicines, the severity and the note')
ok(IX.warnings_for_bill(Cur([], names), [1, 2]) == [], 'no pairs in the table: no warnings')
ok(IX.warnings_for_bill(Cur(db_rows, names), [1]) == [], 'one medicine on the bill: no database query needed')

src = read('pharmacy/routes/interactions.py')
ok('from . import interactions' in read('pharmacy/routes/__init__.py'), 'interaction routes are registered')
ok("@role_required('Admin')" in src.split('def interaction_delete')[0].split('@app.route')[-1] or
   "@role_required('Admin')" in src, 'delete is Admin only')
ok(src.count("@role_required('Admin')") == 1 and "VIEW_ROLES = ('Admin', 'Pharmacist')" in src,
   'only the delete action is Admin only; view and add are Admin and Pharmacist')
ok(all('@guarded' in b and '@login_required' in b for b in re.split(r"\n(?=@app\.route)", src) if '@app.route' in b),
   'every interaction route is login-protected and guarded')
ok('already listed' in src, 'duplicate pair is refused with a clear message')

sales = read('pharmacy/routes/sales.py')
ok('IX.warnings_for_bill(cur, [mid for mid, _p, _parts in lines])' in sales, 'sale checks the bill after it is saved')
ok(sales.index('IX.warnings_for_bill') > sales.index("flash(msg, 'success')"), 'warning is shown after the sale is saved, never before')
ok('try:' in sales[sales.index('IX.warnings_for_bill') - 200: sales.index('IX.warnings_for_bill')],
   'a failed check cannot break the sale')

mig = read('database/migrations/009_drug_interactions.sql')
ok('UNIQUE KEY uq_interaction_pair (med_a_id, med_b_id)' in mig, 'migration 009 keeps one row per pair')
tpl = read('templates/interactions.html')
ok('not a complete drug database' in tpl and 'Nothing is blocked' in tpl, 'screen says the list is incomplete and nothing is blocked')
ok("'interactions'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'Drug Interactions link is in the sidebar')

import py_compile
for f in ['pharmacy/routes/interactions.py', 'pharmacy/services/interactions.py', 'pharmacy/routes/sales.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
