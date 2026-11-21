"""v78: deleting a user. Rules for history, login rows, and wiring. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import user_history as UH
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

class Cur:
    def __init__(self, counts): self.counts = counts; self.last = None; self.sql = []
    def execute(self, sql, p=None):
        self.sql.append(' '.join(sql.split())); self.last = (sql, p)
    def fetchall(self):
        return [{'TABLE_NAME': t} for t in ['users', 'sales', 'chat_history', 'audit_log', 'remember_tokens',
                                            'api_tokens', 'stock_adjustments', 'drip_injections']]
    def fetchone(self):
        import re
        t = re.search(r'FROM `(\w+)`', self.last[0]).group(1)
        return {'n': self.counts.get(t, 0)}

tables = UH.history_tables(Cur({}))
ok('sales' in tables and 'stock_adjustments' in tables and 'drip_injections' in tables, 'work tables count as history')
ok('users' not in tables and 'remember_tokens' not in tables and 'api_tokens' not in tables, 'the user table and login tables are not history')
ok('audit_log' not in tables, 'audit lines (written at every login) are not history')

ok(UH.history_counts(Cur({}), 7) == {}, 'a user with no work rows has no history')
c = Cur({'sales': 12, 'stock_adjustments': 3})
counts = UH.history_counts(c, 7)
ok(counts == {'sales': 12, 'stock_adjustments': 3}, 'history counts are per table')
ok(all(p == (7,) for sql, p in [c.last] if p) and any('WHERE user_id = %s' in s for s in c.sql), 'counts use the user id as a parameter')
txt = UH.summary({'sales': 12, 'stock_adjustments': 3})
ok(txt == '12 sales, 3 stock changes', 'summary is plain words, biggest first')
ok('drip/injection records' in UH.summary({'drip_injections': 2}), 'new tables get readable names')

route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'users.py'), encoding='utf-8').read()
body = route.split('def delete_user')[1].split('@app.route')[0]
ok('UH.all_references(cur, uid)' in body, 'delete checks every work table, not only sales and chats')
ok('for t in UH.LOGIN_TABLES' in body, 'login rows are removed with the user')
_elif = body.split('elif counts:')[1].split('else:')[0] if 'elif counts:' in body else ''
ok('is_active=0' in _elif and 'reassign_references' in body.split('if counts and force:')[1].split('elif counts:')[0],
   'by default a user with history is turned OFF; permanent delete first moves the records')
ok('turned OFF instead' in body and 'Nothing was lost' in body, 'the message says what happened and that nothing was lost')
tpl = open(_os.path.join(ROOT, 'templates', 'users.html'), encoding='utf-8').read()
ok('sirf <b>band (OFF)</b> hota hai' in tpl, 'the delete dialog says the account may be turned OFF')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
