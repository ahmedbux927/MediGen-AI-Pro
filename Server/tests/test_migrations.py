"""Numbered schema migrations (backend track, B2): file rules, order, run-once, stop on error. No MySQL needed.
Run: python tests/test_migrations.py
"""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import migrations as M

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def write(folder, name, text):
    with open(os.path.join(folder, name), 'w', encoding='utf-8') as fh:
        fh.write(text)

ok(M.split_statements("-- note;\nCREATE TABLE a (x INT);\n\nINSERT INTO a VALUES (1);\n") ==
   ['CREATE TABLE a (x INT)', 'INSERT INTO a VALUES (1)'], 'split: comments ignored, statements separated')

folder = tempfile.mkdtemp()
write(folder, '002_second.sql', 'CREATE TABLE b (x INT);')
write(folder, '001_first.sql', 'CREATE TABLE a (x INT);\nCREATE TABLE a2 (x INT);')
write(folder, 'notes.txt', 'ignored')
write(folder, 'bad-name.sql', 'ignored')
loaded = M.load_migrations(folder)
ok([v for v, _, _ in loaded] == [1, 2], 'files load in number order, other names ignored')
ok(loaded[0][2] == ['CREATE TABLE a (x INT)', 'CREATE TABLE a2 (x INT)'], 'statements of a file are split')

dup = tempfile.mkdtemp()
write(dup, '003_a.sql', 'SELECT 1;'); write(dup, '003_b.sql', 'SELECT 2;')
try:
    M.load_migrations(dup); ok(False, 'a repeated number is refused')
except ValueError:
    ok(True, 'a repeated number is refused')

class FakeCur:
    def __init__(self, applied=(), fail_on=None):
        self.applied, self.fail_on, self.log = list(applied), fail_on, []
        self._last = ''
    def execute(self, sql, params=None):
        self.log.append((' '.join(sql.split()), params)); self._last = sql
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError('boom')
    def fetchall(self):
        if self._last.startswith('SELECT version FROM schema_version'):
            return [{'version': v} for v in self.applied]
        return []

cur = FakeCur()
done = M.run_migrations(cur, folder)
ok(done == [1, 2], 'first run applies both migrations')
ok(sum(1 for s, _ in cur.log if s.startswith('INSERT INTO schema_version')) == 2, 'each applied version is recorded')
ok(cur.log[0][0].startswith('CREATE TABLE IF NOT EXISTS schema_version'), 'the version table is created first')

cur2 = FakeCur(applied=[1, 2])
ok(M.run_migrations(cur2, folder) == [], 'second run applies nothing (run once)')
ok(not any(s.startswith('CREATE TABLE a') for s, _ in cur2.log), 'applied migrations are not run again')

cur3 = FakeCur(applied=[1], fail_on='CREATE TABLE b')
try:
    M.run_migrations(cur3, folder); ok(False, 'a failing migration raises')
except RuntimeError:
    ok(True, 'a failing migration raises')
ok(not any(s.startswith('INSERT INTO schema_version') and p == (2, 'second') for s, p in cur3.log),
   'a failed migration is not recorded as applied')

real = M.load_migrations()
ok(any(v == 2 and n == 'sale_guard' for v, n, _ in real), 'project migration 002_sale_guard.sql is found')
guard_sql = [st for v, n, sts in real if n == 'sale_guard' for st in sts]
ok(len(guard_sql) == 1 and guard_sql[0].startswith('CREATE TABLE IF NOT EXISTS sale_guard'),
   'sale_guard migration is one idempotent CREATE TABLE IF NOT EXISTS')

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
