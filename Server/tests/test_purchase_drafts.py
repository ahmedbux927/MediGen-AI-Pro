"""Purchase drafts (v87.05): rules, grouping, quantity checks, and wiring. No MySQL needed.
Run: python tests/test_purchase_drafts.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import purchase_drafts as PD

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

ok(PD.parse_qty('5') == 5 and PD.parse_qty(' 0 ') == 0, 'quantity 5 and 0 are accepted')
for bad, label in [('abc', 'text is refused'), ('-1', 'negative is refused'), ('100001', 'above the limit is refused'), ('2.5', 'decimal is refused')]:
    try:
        PD.parse_qty(bad); ok(False, label)
    except PD.DraftError:
        ok(True, label)

rows = [{'medicine_id': 1, 'name': 'Panadol', 'qty': 10, 'cost': 50.0},
        {'medicine_id': 2, 'name': 'Syrup', 'qty': 4, 'cost': 120.0},
        {'medicine_id': 3, 'name': 'Cream', 'qty': 6, 'cost': 80.0}]
groups = PD.group_by_supplier(rows, {1: 7, 2: 7, 3: 9})
ok(sorted(groups.keys(), key=lambda k: (k is None, k)) == [7, 9], 'one group per supplier')
ok([r['name'] for r in groups[7]] == ['Panadol', 'Syrup'], 'supplier 7 gets its two items')
none = PD.group_by_supplier(rows, {1: 7})
ok(None in none and len(none[None]) == 2, 'items with no supplier history go to one draft with no supplier')
ok(PD.lines_total([{'quantity': 10, 'unit_cost': 50.0}, {'quantity': 4, 'unit_cost': 120.5}]) == 982.0,
   'estimated total adds quantity times unit cost')
ok(PD.lines_total([]) == 0, 'empty draft total is zero')

class Cur:
    def __init__(self, open_ids=(), supplier_rows=()):
        self.open_ids, self.supplier_rows = list(open_ids), list(supplier_rows)
        self.log, self.lastrowid, self._all = [], 0, []
    def execute(self, sql, p=None):
        s = ' '.join(sql.split()); self.log.append((s, p))
        if s.startswith('SELECT DISTINCT l.medicine_id'):
            self._all = [{'medicine_id': m} for m in self.open_ids]
        elif s.startswith('SELECT pi.medicine_id, po.supplier_id'):
            self._all = self.supplier_rows
        elif s.startswith('INSERT INTO purchase_drafts'):
            self.lastrowid = 100 + sum(1 for x, _ in self.log if x.startswith('INSERT INTO purchase_drafts'))
    def fetchall(self):
        return self._all

sugg = [{'medicine_id': 1, 'name': 'Panadol', 'qty': 10, 'cost': 50.0},
        {'medicine_id': 2, 'name': 'Syrup', 'qty': 4, 'cost': 120.0},
        {'medicine_id': 3, 'name': 'Cream', 'qty': 0, 'cost': 80.0}]
c = Cur(open_ids=[1], supplier_rows=[{'medicine_id': 2, 'supplier_id': 7}])
drafts, lines = PD.create_from_suggestions(c, 5, sugg)
ok(drafts == 1 and lines == 1, 'item already on an open draft is not added again; zero-qty item is skipped')
ins_lines = [p for s_, p in c.log if s_.startswith('INSERT INTO purchase_draft_lines')]
ok(len(ins_lines) == 1 and ins_lines[0][1:] == (2, 4, 120.0), 'the line keeps medicine, quantity and cost')
ok(not any(s_.startswith(('INSERT INTO purchase_items', 'UPDATE medicines', 'INSERT INTO purchase_orders'))
           for s_, _ in c.log), 'creating drafts never writes purchases or stock')

c2 = Cur(open_ids=[], supplier_rows=[])
d2, l2 = PD.create_from_suggestions(c2, 5, sugg[:2])
ok(d2 == 1 and l2 == 2, 'no supplier history: both items go into one draft with no supplier')
ok(PD.create_from_suggestions(Cur(open_ids=[1, 2]), 5, sugg[:2]) == (0, 0), 'nothing new: no drafts are created')

class Cur2:
    def __init__(self): self.log = []
    def execute(self, sql, p=None): self.log.append((' '.join(sql.split()), p))
c3 = Cur2()
PD.apply_quantities(c3, 9, [(1, 12), (2, 0)])
ok(c3.log[0][0].startswith('UPDATE purchase_draft_lines SET quantity') and c3.log[0][1] == (12, 9, 1),
   'a quantity updates that line')
ok(c3.log[1][0].startswith('DELETE FROM purchase_draft_lines') and c3.log[1][1] == (9, 2),
   'a quantity of 0 removes the line')

src = read('pharmacy/routes/purchase_drafts.py')
ok('from . import purchase_drafts' in read('pharmacy/routes/__init__.py'), 'draft routes are registered')
ok("DRAFT_ROLES = ('Admin', 'Pharmacist')" in src, 'only Admin and Pharmacist')
ok("if not draft or draft['status'] != 'draft'" in src, 'saving is refused unless the draft is open')
ok("'draft', 'draft'" not in src and "_change_status(draft_id, 'cancelled', 'draft'" in src, 'cancel only from an open draft')
ok(not re.search(r"UPDATE medicines|INSERT INTO purchase_items|trg_", src), 'draft routes never touch stock or purchases')
ok(all('@guarded' in b and '@login_required' in b for b in re.split(r"\n(?=@app\.route)", src) if '@app.route' in b),
   'every draft route is login-protected and guarded')
ok('from pharmacy.routes.purchase_suggest import _suggestion_rows' in src, 'drafts use the same suggestion rules as the screen')
mig = read('database/migrations/008_purchase_drafts.sql')
ok('CREATE TABLE IF NOT EXISTS purchase_drafts' in mig and 'CREATE TABLE IF NOT EXISTS purchase_draft_lines' in mig,
   'migration 008 creates the two draft tables')
ok("'medicine_id': m.get('medicine_id'), 'cost': cost" in read('pharmacy/routes/purchase_suggest.py'),
   'suggestion rows now carry medicine id and cost (for drafts)')
ok("'purchase_drafts'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'Purchase Drafts link is in the sidebar')
for t in ['purchase_drafts.html', 'purchase_draft.html']:
    ok(os.path.exists(os.path.join(ROOT, 'templates', t)), t + ' exists')

import py_compile
for f in ['pharmacy/routes/purchase_drafts.py', 'pharmacy/services/purchase_drafts.py', 'pharmacy/routes/purchase_suggest.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
