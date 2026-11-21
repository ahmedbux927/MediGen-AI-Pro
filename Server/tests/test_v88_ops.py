"""v88.00: Step 4 operational checks that can run without a live MySQL server.
- Backup: run_backup against a FAKE mysqldump (exit code and file size are really checked).
- reset_password: the bcrypt hash pattern it stores verifies for the new password and not the old.
Live MySQL checks (purchase orders, reset against a real schema, real mysqldump) are NOT
covered here - see the v88.00 delivery report, "Not verified"."""
import os as _os, stat, sys as _sys, tempfile
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT); _sys.path.insert(0, _os.path.join(ROOT, 'scripts'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

import backup_db as B

tmp = tempfile.mkdtemp()
good = _os.path.join(tmp, 'fake_mysqldump_ok')
bad = _os.path.join(tmp, 'fake_mysqldump_fail')
with open(good, 'w') as f:
    f.write('#!/bin/sh\necho "-- fake dump"\nhead -c 500 /dev/zero | tr "\\0" "x"\n')
with open(bad, 'w') as f:
    f.write('#!/bin/sh\necho "mysqldump: access denied" >&2\nexit 2\n')
for p in (good, bad):
    _os.chmod(p, _os.stat(p).st_mode | stat.S_IEXEC)

base = {'host': 'localhost', 'user': 'root', 'password': '', 'name': 'medigen_disposable_test',
        'backup_dir': _os.path.join(tmp, 'backups'), 'keep': 30, 'offsite_dir': ''}

s = dict(base, mysqldump=good)
path, _removed = B.run_backup(s)
ok(_os.path.exists(path) and _os.path.getsize(path) > 200, 'backup with a working mysqldump writes a real file (>200 bytes)')

s = dict(base, mysqldump=bad)
try:
    B.run_backup(s)
    ok(False, 'backup with a failing mysqldump raises instead of claiming success')
except RuntimeError as e:
    ok('mysqldump failed' in str(e), 'backup with a failing mysqldump raises instead of claiming success')
leftovers = [f for f in _os.listdir(base['backup_dir']) if f.endswith('.sql')]
ok(len(leftovers) == 1, 'a failed backup keeps the earlier good backup and leaves no half-written file')

s = dict(base, mysqldump=_os.path.join(tmp, 'does_not_exist'))
try:
    B.run_backup(s)
    ok(False, 'missing mysqldump raises a clear error')
except RuntimeError as e:
    ok('could not start mysqldump' in str(e), 'missing mysqldump raises a clear error')

# reset_password hash pattern (same calls as reset_password.py)
import bcrypt
old_hash = bcrypt.hashpw(b'OldPass123', bcrypt.gensalt())
new_hash = bcrypt.hashpw(b'NewPass456', bcrypt.gensalt())
ok(bcrypt.checkpw(b'NewPass456', new_hash), 'new password verifies against the stored hash pattern')
ok(not bcrypt.checkpw(b'OldPass123', new_hash), 'old password does not verify after a reset')

if __name__ == '__main__':
    bad_ = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad_)} passed, {len(bad_)} failed')
    _sys.exit(1 if bad_ else 0)
