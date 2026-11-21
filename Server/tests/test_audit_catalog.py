"""
Audit coverage check (v26): categories, customers and suppliers add/delete are written to the audit log.
Run: python tests/test_audit_catalog.py
"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

src = open(os.path.join(ROOT, 'pharmacy/routes/catalog.py'), encoding='utf-8').read()
for action in ['category.add', 'category.delete', 'customer.add', 'customer.delete', 'supplier.add', 'supplier.delete']:
    ok(f"audit(cur, '{action}'" in src, f'{action} is audited')

# Each audit call must come before its commit, so the log and the change are saved together.
for m in re.finditer(r"audit\(cur, '([a-z]+\.(?:add|delete))'", src):
    after = src[m.end():m.end() + 200]
    ok('mysql.connection.commit()' in after.split('except')[0], f"{m.group(1)} is written before the commit")

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
