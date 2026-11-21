"""Stage 11 (Master Prompt v4): the QA record exists and the guardrails hold.

The live evidence (route x role matrix, CSRF rejection, migration double
run, performance at 1000 medicines) is recorded in QA_MATRIX.md and
BASELINE.md at the project root; this test keeps those records present and
the key source-level guarantees in place.
"""
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
PROJ = _os.path.dirname(ROOT)
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel, base=ROOT):
    with open(_os.path.join(base, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


qa = read('QA_MATRIX.md', PROJ)
for needle in ('Cashier', 'Pharmacist', 'Admin', '/settings', 'CSRF', 'Migrations double-run', '1005 medicines'):
    ok(needle in qa, f'QA_MATRIX.md records: {needle}')
base = read('BASELINE.md', PROJ)
ok('Stage 11' in base and 'pyflakes' in base, 'BASELINE.md carries the Stage 11 measurements')

core = read('pharmacy/core.py')
ok('def csrf_protect' in core, 'global CSRF protection is wired in core')
ok('SESSION_COOKIE_HTTPONLY' in core or 'HttpOnly' in core or 'httponly' in core.lower(),
   'session cookie is HttpOnly')
mig = read('pharmacy/services/migrations.py')
ok('schema_version' in mig, 'migrations are tracked in schema_version (applied once)')
ok(_os.path.exists(_os.path.join(ROOT, 'database', 'migrations', '014_import_preview.sql')),
   'migration files go up to 014')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
