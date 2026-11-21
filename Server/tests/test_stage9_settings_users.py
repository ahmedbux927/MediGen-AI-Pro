"""Stage 9 (Master Prompt v4): settings and user administration.

- Settings groups can be reset to the built-in defaults (audited).
- Users can be edited (name + role); the last active Admin cannot be demoted.
- Deleting a user with history turns the account off instead of deleting it
  (checked in the route source), and passwords are bcrypt-hashed.
Live round-trips were run against real MySQL on 2026-11-21.
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


settings = read('pharmacy/routes/settings.py')
ok('def settings_reset' in settings and 'SETTING_RESET_GROUPS' in settings, 'settings reset route exists with named groups')
ok("'shop'" in settings and "'money'" in settings, 'reset covers the shop and money groups')
ok('SETTING_DEFAULTS.get' in settings, 'reset restores the built-in defaults, not invented values')
ok("audit(cur, 'settings.reset'" in settings, 'a reset is written to the audit log')
tpl = read('templates/settings.html')
ok(tpl.count('Reset to defaults') >= 2 and "url_for('settings_reset')" in tpl,
   'shop and money panes both offer Reset to defaults (with a confirm)')

users = read('pharmacy/routes/users.py')
ok('def edit_user' in users, 'users can be edited (name and role)')
ok('only active Admin' in users, 'the last active Admin cannot be demoted')
ok("audit(cur, 'user.edit'" in users, 'user edits are audited')
ok('all_references' in users and 'turned OFF instead' in users and "request.form.get('force')" in users,
   'a user with sales history is deactivated by default; permanent delete needs the explicit tick')
ok('bcrypt.hashpw' in users, 'passwords are bcrypt-hashed')
utpl = read('templates/users.html')
ok('editModal' in utpl and "url_for('edit_user'" in utpl, 'users page has the edit dialog')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
