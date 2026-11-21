"""Software license (v87.09): key rules, banner and warning-only promise, and the key tool. No MySQL needed.
Run: python tests/test_license.py
"""
import os, sys, importlib.util
from datetime import date
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import license as LIC

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

SECRET = 'test-secret-value'
TODAY = date(2026, 10, 29)
M = LIC.machine_id()

k = LIC.make_key(SECRET, 'Medicose', '2027-12-31')
st = LIC.check_key(k, SECRET, TODAY, M)
ok(st['state'] == 'valid' and st['customer'] == 'Medicose' and st['expires'] == '2027-12-31', 'a good key is valid with customer and expiry')
ok(LIC.check_key(k, 'other-secret', TODAY, M)['state'] == 'invalid', 'a key made with another secret is invalid')
tampered = k[:-2] + ('AA' if k[-2:] != 'AA' else 'BB')
ok(LIC.check_key(tampered, SECRET, TODAY, M)['state'] == 'invalid', 'a changed signature is invalid')
parts = k.split('.')
forged_payload = LIC.make_key(SECRET, 'Medicose', '2099-01-01')  # valid key, but we swap the payload below
evil = parts[0] + '.' + LIC._b64e(b'{"c":"x","e":"2099-01-01","m":"*"}') + '.' + parts[2]
ok(LIC.check_key(evil, SECRET, TODAY, M)['state'] == 'invalid', 'editing the expiry in the payload is detected')
ok(LIC.check_key('hello', SECRET, TODAY, M)['state'] == 'invalid', 'random text is invalid')
ok(LIC.check_key('MG1.abc', SECRET, TODAY, M)['state'] == 'invalid', 'a short key is invalid')
ok(LIC.check_key('', SECRET, TODAY, M)['state'] == 'missing', 'empty key is missing')
ok(LIC.check_key(k, '', TODAY, M)['state'] == 'no_secret', 'no secret on this PC: says so, does not crash')

ok(LIC.check_key(LIC.make_key(SECRET, 'A', '2026-10-01'), SECRET, TODAY, M)['state'] == 'expired', 'past expiry is expired')
ok(LIC.check_key(LIC.make_key(SECRET, 'A', '2026-11-05'), SECRET, TODAY, M)['state'] == 'expiring', 'within 14 days is expiring')
ok(LIC.check_key(LIC.make_key(SECRET, 'A', '2026-11-30'), SECRET, TODAY, M)['state'] == 'valid', 'more than 14 days left is valid')
ok(LIC.check_key(LIC.make_key(SECRET, 'A', '2026-10-29'), SECRET, TODAY, M)['state'] == 'expiring', 'expires today is still usable (expiring, not expired)')

pc_key = LIC.make_key(SECRET, 'A', '2027-01-01', machine='0123456789abcdef')
ok(LIC.check_key(pc_key, SECRET, TODAY, M)['state'] == 'wrong_pc', 'a key tied to another PC is wrong_pc')
ok(LIC.check_key(LIC.make_key(SECRET, 'A', '2027-01-01', machine=M), SECRET, TODAY, M)['state'] == 'valid', 'a key tied to this PC is valid')
ok(LIC.check_key(LIC.make_key(SECRET, 'A', 'not-a-date'), SECRET, TODAY, M)['state'] == 'invalid', 'a bad expiry date is invalid')

ok(len(M) == 16 and M == LIC.machine_id(), 'machine id is short and stable')

src = read('pharmacy/routes/license.py')
ok('except Exception:\n        app.logger.exception(\'license check failed\')\n        return {\'license_banner\': \'\'}' in src,
   'the banner check never breaks a page')
ok("if st['state'] in ('invalid', 'no_secret', 'missing', 'wrong_pc')" in src, 'a bad key is not saved; expired keys are saved (warning)')
ok("@role_required('Admin')" in src and src.count("@role_required('Admin')") == 2, 'only Admin can view and save the key')
ok("ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)" in src, 'key is saved in app settings')
ok(src.count('@guarded') == 2 and src.count('@login_required') == 2, 'both license routes are login-protected and guarded')

for f in ['pharmacy/services/sales.py', 'pharmacy/routes/sales.py', 'pharmacy/services/pos.py', 'pharmacy/services/cash_drawer.py']:
    ok('license' not in read(f).lower(), f'{f} does not check the license (billing is never blocked)')

ok("license_banner" in read('templates/base.html'), 'base page shows the warning banner when needed')
ok("'license_page'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'License link is in the Admin sidebar')
ok('warning only' in read('templates/license.html').lower() or 'does not stop billing' in read('templates/license.html').lower(),
   'license page says the key never stops billing')

spec = importlib.util.spec_from_file_location('mk', os.path.join(ROOT, 'scripts', 'make_license.py'))
mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
ok(hasattr(mk, 'main') and 'make_key' in read('scripts/make_license.py'), 'key tool exists and uses the same key maker')

import py_compile
for f in ['pharmacy/routes/license.py', 'pharmacy/services/license.py', 'scripts/make_license.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
