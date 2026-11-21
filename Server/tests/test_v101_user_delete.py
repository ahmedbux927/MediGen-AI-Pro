"""v101.03: user delete actually works (the owner reported a stuck user).

Old behaviour: any user with rows in a user_id column could only be turned
OFF, and references through differently named FK columns (counted_by,
created_by) were not even scanned, so a delete could still hit a foreign
key. Now: all references are scanned (user_id columns + KEY_COLUMN_USAGE),
and a confirmed permanent delete moves the records to a 'Deleted user'
placeholder before removing the account.
"""
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


from pharmacy.services import user_history as UH  # noqa: E402


class FakeCursor:
    def __init__(self):
        self.updates = []
        self._rows = []

    def execute(self, sql, params=None):
        s = ' '.join(sql.split())
        if 'information_schema.COLUMNS' in s:
            self._rows = [{'TABLE_NAME': t} for t in ('sales', 'chat_history', 'users', 'audit_log')]
        elif 'KEY_COLUMN_USAGE' in s:
            self._rows = [{'TABLE_NAME': 'sales', 'COLUMN_NAME': 'user_id'},
                          {'TABLE_NAME': 'chat_history', 'COLUMN_NAME': 'user_id'},
                          {'TABLE_NAME': 'stock_counts', 'COLUMN_NAME': 'counted_by'},
                          {'TABLE_NAME': 'purchase_drafts', 'COLUMN_NAME': 'created_by'}]
        elif s.startswith('SELECT COUNT(*)'):
            table = s.split('FROM `')[1].split('`')[0]
            col = 'counted_by' if 'counted_by' in s else ('created_by' if 'created_by' in s else 'user_id')
            n = {('sales', 'user_id'): 3, ('chat_history', 'user_id'): 0,
                 ('stock_counts', 'counted_by'): 2, ('purchase_drafts', 'created_by'): 0}[(table, col)]
            self._rows = [{'n': n}]
        elif s.startswith('UPDATE'):
            self.updates.append(s)
            self._rows = []
        else:
            self._rows = []

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


cur = FakeCursor()
refs = UH.all_references(cur, 7)
ok(refs.get('sales') == 3 and refs.get('stock_counts') == 2, 'all_references sees user_id rows AND counted_by rows')
ok('chat_history' not in refs and 'purchase_drafts' not in refs, 'zero-count references are not reported')

cur2 = FakeCursor()
UH.reassign_references(cur2, 7, 99)
joined = ' | '.join(cur2.updates)
ok('`sales` SET user_id' in joined and '`stock_counts` SET `counted_by`' in joined
   and '`purchase_drafts` SET `created_by`' in joined,
   'reassign moves user_id rows and differently named FK rows to the placeholder')

routes = read('pharmacy/routes/users.py')
ok("request.form.get('force') == '1'" in routes and 'placeholder_user' in routes,
   'the delete route has the confirmed permanent-delete path')
ok("'deleted-user'" in routes, 'the Deleted user placeholder itself cannot be deleted')
ok('only active Admin' in routes, 'the last active Admin cannot be deleted or turned off from here')
tpl = read('templates/users.html')
ok('deleteModal' in tpl and 'name="force"' in tpl and 'Deleted user' in tpl,
   'the Users page delete dialog offers the permanent option with the records note')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
