"""Photo reader readiness (v87.06): status rules with a fake Tesseract. No real OCR needed.
Run: python tests/test_ocr_readiness.py
"""
import os, sys, types, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import rx_scan as RS

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

def fake_run(version_out, langs_out, raise_on=None):
    def run(cmd, **kw):
        if raise_on:
            raise raise_on
        if '--version' in cmd:
            return types.SimpleNamespace(stdout=version_out, stderr='')
        return types.SimpleNamespace(stdout=langs_out, stderr='')
    return run

real_exe, real_run = RS._tesseract_exe, subprocess.run

RS._tesseract_exe = lambda: None
st = RS._check_tesseract()
ok(st['ready'] is False and st['exe'] is None and 'not found' in st['message'], 'no Tesseract: not ready, clear message')

RS._tesseract_exe = lambda: r'C:\Tools\tesseract.exe'
subprocess.run = fake_run('tesseract 5.3.0\n leptonica', 'List of available languages (3):\neng\nosd\nurd\n')
st = RS._check_tesseract()
ok(st['ready'] is True and st['version'] == 'tesseract 5.3.0' and 'eng' in st['languages'], 'installed with English: ready, version shown')

subprocess.run = fake_run('tesseract 5.3.0', 'List of available languages (1):\nosd\n')
st = RS._check_tesseract()
ok(st['ready'] is False and "'eng' language data is missing" in st['message'], 'English data missing: not ready, says what to fix')

import subprocess as sp
subprocess.run = fake_run('', '', raise_on=OSError('blocked'))
st = RS._check_tesseract()
ok(st['ready'] is False and 'could not be started' in st['message'], 'Tesseract that cannot start: not ready, no crash')

subprocess.run = fake_run('tesseract 5.3.0', 'List of available languages (1):\neng\n')
RS._OCR_CACHE.update({'at': 0.0, 'value': None})
a = RS.ocr_status()
subprocess.run = fake_run('tesseract 9.9.9', 'List of available languages (1):\neng\n')
b = RS.ocr_status()
ok(a is b and a['version'] == 'tesseract 5.3.0', 'result is cached for a minute (no check on every page load)')
c = RS.ocr_status(force=True)
ok(c['version'] == 'tesseract 9.9.9', 'force re-checks now')

subprocess.run = real_run
RS._tesseract_exe = real_exe
RS._OCR_CACHE.update({'at': 0.0, 'value': None})

src = read('pharmacy/routes/rx_scan.py')
ok("ocr=RXS.ocr_status()" in src, 'scan page gets the readiness status')
tpl = read('templates/rx_scan.html')
ok('{% if ocr.ready %}' in tpl and 'TESSERACT_INSTALL_ROMAN_URDU.md' in tpl, 'scan page shows a ready or not-ready banner with the install guide')
ok(os.path.exists(os.path.join(ROOT, 'TESSERACT_INSTALL_ROMAN_URDU.md')), 'install guide is in the project')

import py_compile
for f in ['pharmacy/services/rx_scan.py', 'pharmacy/routes/rx_scan.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
