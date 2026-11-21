"""Stock count with variance approval (Phase 3): rules and the database steps, mock cursor. No MySQL needed.
Run: python tests/test_stock_count.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import stock_count as SC
from pharmacy.services import migrations as M

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def raises(fn, part, label):
    try:
        fn(); ok(False, label)
    except SC.CountError as e:
        ok(part in str(e), label)

ok(SC.can_move('open', 'submitted') and not SC.can_move('approved', 'open'), 'states: open to submitted only, approved is final')
ok(not SC.can_move('cancelled', 'open'), 'a cancelled count cannot be reopened')
ok(SC.variance(10, 7) == -3 and SC.variance(10, 12) == 2, 'variance = counted - system')

lines = [{'medicine_id': 1, 'system_qty': 10, 'counted_qty': 7},
         {'medicine_id': 2, 'system_qty': 5, 'counted_qty': 5},
         {'medicine_id': 3, 'system_qty': 0, 'counted_qty': 4},
         {'medicine_id': 4, 'system_qty': 9, 'counted_qty': None}]
s = SC.summarise(lines, {1: 100, 2: 20, 3: 50, 4: 1})
ok(s == {'lines': 4, 'counted': 3, 'uncounted': 1, 'changed': 2, 'short_units': 3, 'over_units': 4,
         'value_change': round(-3 * 100 + 4 * 50, 2)}, 'summary: short 3, over 4, value change -300 + 200 = -100')
ok(SC.conflicts(lines, {1: 10, 2: 5, 3: 0, 4: 99}) == [], 'no conflict when stock is unchanged (uncounted line ignored)')
ok(SC.conflicts(lines, {1: 8, 2: 5, 3: 0, 4: 9}) == [1], 'a sale during the count is a conflict on a counted line')

class Cur:
    """Records statements. Returns scripted answers for the status and line queries."""
    def __init__(self, status='open', lines=(), updated=1, current=None):
        self.status, self.lines, self.updated = status, list(lines), updated
        self.current = current or {}
        self.log, self.lastrowid, self.rowcount, self._last = [], 1, 1, ''
    def execute(self, sql, p=None):
        self.log.append((' '.join(sql.split()), p)); self._last = sql
        if sql.startswith('INSERT INTO stock_counts'): self.lastrowid = 7
        if sql.startswith('UPDATE stock_count_lines'): self.rowcount = self.updated
    def fetchone(self):
        if 'FROM stock_counts WHERE count_id' in self._last or 'FROM stock_counts WHERE status' in self._last:
            return {'status': self.status, 'count_id': 7} if self.status else None
        if 'COUNT(*) AS n FROM stock_count_lines' in self._last:
            return {'n': sum(1 for l in self.lines if l['counted_qty'] is None)}
        return None
    def fetchall(self):
        if 'FROM stock_count_lines l JOIN medicines' in self._last:
            return [dict(l, name='M%d' % l['medicine_id'], stock_quantity=self.current.get(l['medicine_id'], l['system_qty']))
                    for l in self.lines]
        return [{'medicine_id': 1, 'stock_quantity': 10}]

audits = []
def audit(cur, action, entity=None, entity_id=None, details='', before=None, after=None, status='ok'):
    audits.append((action, entity_id))

raises(lambda: SC.start_count(Cur(status='open'), 1), 'already in progress', 'a second count cannot start while one is open')
c = Cur(status=None); ok(SC.start_count(c, 1) == 7 and sum(1 for s_, _ in c.log if s_.startswith('INSERT INTO stock_count_lines')) == 1,
                         'start: one line per medicine, with the system stock saved')
raises(lambda: SC.record_count(Cur(status='submitted'), 7, 1, 5, 1), 'not open', 'counting is locked after submit')
raises(lambda: SC.record_count(Cur(status='open'), 7, 1, 'x', 1), 'whole number', 'text quantity is refused with a clear message')
raises(lambda: SC.record_count(Cur(status='open'), 7, 1, -1, 1), '0 to 1,000,000', 'negative quantity is refused')
raises(lambda: SC.record_count(Cur(status='open', updated=0), 7, 9, 3, 1), 'not part of the count', 'medicine outside the count is refused')
ok(SC.record_count(Cur(status='open'), 7, 1, '5', 1) is None, 'a valid count is recorded')
raises(lambda: SC.submit_count(Cur(status='open', lines=[{'medicine_id': 1, 'system_qty': 1, 'counted_qty': None}]), 7),
       'not counted yet', 'submit refused while any line is uncounted')
ok(SC.submit_count(Cur(status='open', lines=[{'medicine_id': 1, 'system_qty': 1, 'counted_qty': 1}]), 7) is None, 'submit works when all lines are counted')
raises(lambda: SC.approve_count(Cur(status='submitted'), 7, 2, 'Pharmacist', audit), 'Only an Admin', 'only an Admin can approve')
raises(lambda: SC.approve_count(Cur(status='open'), 7, 2, 'Admin', audit), 'Submit it first', 'an open count cannot be approved')
clash_lines = [{'medicine_id': 1, 'system_qty': 10, 'counted_qty': 7}]
raises(lambda: SC.approve_count(Cur(status='submitted', lines=clash_lines, current={1: 9}), 7, 2, 'Admin', audit),
       'Stock changed', 'approval refused when stock changed during the count')
audits.clear()
c = Cur(status='submitted', lines=[{'medicine_id': 1, 'system_qty': 10, 'counted_qty': 7},
                                   {'medicine_id': 2, 'system_qty': 5, 'counted_qty': 5}])
n = SC.approve_count(c, 7, 2, 'Admin', audit)
ok(n == 1, 'approval changes only lines with a variance')
ok(any(s_.startswith('UPDATE medicines SET stock_quantity=') and p == (7, 1) for s_, p in c.log),
   'stock set to the counted quantity')
adj = [p for s_, p in c.log if s_.startswith('INSERT INTO stock_adjustments')]
ok(len(adj) == 1 and adj[0] == (1, 2, -3, 10, 7, 'Stock count', 'Count #7'), 'one adjustment row: -3, from 10 to 7, reason Stock count')
ok(audits == [('stock.count_approved', 1)], 'one audit row for the changed medicine')
ok(not any('batches' in s_ for s_, _ in c.log), 'batches are not changed by the approval')

raises(lambda: SC.reopen_count(Cur(status='open'), 7), 'Only a submitted count', 'an open count cannot be sent back')
raises(lambda: SC.reopen_count(Cur(status='approved'), 7), 'Only a submitted count', 'an approved count cannot be reopened')
c = Cur(status='submitted')
SC.reopen_count(c, 7)
ok(any(s_.startswith("UPDATE stock_counts SET status='open'") for s_, _ in c.log), 'submitted count goes back to open')
ok(not SC.can_move('cancelled', 'open') and SC.can_move('submitted', 'open'), 'reopen follows the state table')

ok(any(n_ == 'stock_counts' and any('CREATE TABLE IF NOT EXISTS stock_count_lines' in st for st in sts)
       for _, n_, sts in M.load_migrations()), 'migration 003 creates the count tables (idempotent)')
print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
