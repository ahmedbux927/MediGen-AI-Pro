"""Phase 4 backend: controlled-drug register, prescription rule for scheduled medicines, cold-chain log.
Mock cursor only (no MySQL). Run: python tests/test_phase4_backend.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import controlled_register as CR
from pharmacy.services import temperature as T
from pharmacy.services import sales as S
from pharmacy.services.migrations import split_statements

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

class FakeCur:
    def __init__(self, rows=None):
        self.rows, self.sql, self.lastrowid = list(rows or []), [], 0
    def execute(self, sql, params=None):
        self.sql.append((' '.join(sql.split()), params))
        if sql.strip().upper().startswith('INSERT'):
            self.lastrowid += 1
    def fetchall(self):
        return self.rows
    def fetchone(self):
        return self.rows[0] if self.rows else None

def inserts(cur, table):
    return [p for s, p in cur.sql if s.startswith('INSERT INTO ' + table)]

# --- scheduled medicines
cur = FakeCur([{'medicine_id': 5, 'name': 'Morphine 10mg', 'schedule': 'Narcotic'}])
sched = CR.scheduled_items(cur, [5, 6])
ok(sched == {5: ('Narcotic', 'Morphine 10mg')}, 'scheduled_items returns only medicines with a schedule')
ok(CR.scheduled_items(FakeCur(), []) == {}, 'no ids: no query needed')

ok(CR.prescription_missing(sched, None) == ['Morphine 10mg'], 'scheduled item without prescription is reported')
ok(CR.prescription_missing(sched, 12) == [], 'scheduled item with prescription passes')
ok(CR.prescription_missing({}, None) == [], 'no scheduled items: nothing to check')

# --- check_scheduled (service)
lines = [(5, 100.0, [(9, 2), (10, 1)]), (6, 20.0, [(None, 3)])]
cur = FakeCur([{'medicine_id': 5, 'name': 'Morphine 10mg', 'schedule': 'Narcotic'}])
try:
    S.check_scheduled(cur, lines, None)
    ok(False, 'scheduled sale without prescription is refused')
except S.BillError as e:
    ok('Morphine 10mg' in str(e) and 'Prescription needed' in str(e), 'scheduled sale without prescription is refused with name')
got = S.check_scheduled(FakeCur([{'medicine_id': 5, 'name': 'Morphine 10mg', 'schedule': 'Narcotic'}]), lines, 77)
ok(list(got.keys()) == [5], 'with prescription the check returns the scheduled items')
ok(S.check_scheduled(FakeCur([]), lines, None) == {}, 'no scheduled medicines: sale passes without prescription')

# --- register entries
entries = CR.entries_for_sale(lines, {5: ('Narcotic', 'Morphine 10mg')})
ok(entries == [{'medicine_id': 5, 'schedule': 'Narcotic', 'batch_id': 9, 'quantity': 2},
               {'medicine_id': 5, 'schedule': 'Narcotic', 'batch_id': 10, 'quantity': 1}],
   'one register entry per batch part of a scheduled line')
ok(CR.entries_for_sale(lines, {}) == [], 'unscheduled lines produce no entries')

wcur = FakeCur()
n = CR.write_entries(wcur, 44, 3, 8, 77, entries)
ok(n == 2 and len(inserts(wcur, 'controlled_register')) == 2, 'write_entries inserts one row per entry')
ok(inserts(wcur, 'controlled_register')[0] == (44, 5, 'Narcotic', 9, 2, 8, 77, 3), 'register row carries sale, batch, qty, customer, rx, user')

# --- save_sale writes the register only when scheduled is passed
bill = {'total': 300.0, 'paid': 300.0, 'discount': 0.0, 'tax': 0.0}
scur = FakeCur()
S.save_sale(scur, 3, 8, 'Cash', 77, 300.0, bill, lines, 0.0, lambda *a, **k: None, scheduled={5: ('Narcotic', 'Morphine 10mg')})
ok(len(inserts(scur, 'controlled_register')) == 2, 'save_sale with scheduled items writes the register')
scur2 = FakeCur()
S.save_sale(scur2, 3, 8, 'Cash', None, 300.0, bill, lines, 0.0, lambda *a, **k: None)
ok(len(inserts(scur2, 'controlled_register')) == 0, 'save_sale without scheduled items writes no register rows')

# --- triggers: failure is tolerated (no TRIGGER permission)
class NoTrig(FakeCur):
    def execute(self, sql, params=None):
        raise RuntimeError('access denied')
logged = []
class L:
    def warning(self, *a, **k): logged.append(a)
try:
    CR.ensure_register_triggers(NoTrig(), L())
    ok(bool(logged), 'missing TRIGGER permission is logged, app still starts')
except Exception:
    ok(False, 'missing TRIGGER permission is logged, app still starts')
tcur = FakeCur()
CR.ensure_register_triggers(tcur)
ok(any('trg_register_no_update' in s for s, _ in tcur.sql) and any('trg_register_no_delete' in s for s, _ in tcur.sql),
   'both append-only triggers are created')

# --- temperature
from decimal import Decimal
ok(T.parse_reading('5.2') == Decimal('5.2'), 'parse: plain number')
ok(T.parse_reading('5,2') == Decimal('5.2'), 'parse: comma decimal accepted')
for bad in ['abc', '90', '-50', '']:
    try:
        T.parse_reading(bad); ok(False, f'parse: {bad!r} refused')
    except T.TemperatureError:
        ok(True, f'parse: {bad!r} refused')
ok(T.is_in_range(Decimal('2.0')) and T.is_in_range(Decimal('8.0')), 'range: 2.0 and 8.0 are inside (inclusive)')
ok(not T.is_in_range(Decimal('1.9')) and not T.is_in_range(Decimal('8.1')), 'range: 1.9 and 8.1 are outside')

tc = FakeCur()
r = T.record_reading(tc, 'Fridge 1', '4.5', 3, 'morning')
ok(r['in_range'] is True and inserts(tc, 'temperature_logs')[0][2] == 1, 'reading in range is saved with in_range=1')
tc2 = FakeCur()
r2 = T.record_reading(tc2, 'Fridge 1', '9.3', 3)
ok(r2['in_range'] is False and inserts(tc2, 'temperature_logs')[0][2] == 0, 'reading out of range is still saved with in_range=0')
try:
    T.record_reading(FakeCur(), '   ', '4', 3)
    ok(False, 'empty location refused')
except T.TemperatureError:
    ok(True, 'empty location refused')

# --- migration files
for f in ['005_controlled_register.sql', '006_temperature_logs.sql']:
    with open(os.path.join(ROOT, 'database', 'migrations', f), encoding='utf-8') as fh:
        stmts = split_statements(fh.read())
    ok(len(stmts) == 1 and stmts[0].upper().startswith('CREATE TABLE IF NOT EXISTS'), f'{f}: one idempotent CREATE TABLE')

print(f'\nTOTAL {PASS + FAIL}  PASS {PASS}  FAIL {FAIL}')
sys.exit(1 if FAIL else 0)
