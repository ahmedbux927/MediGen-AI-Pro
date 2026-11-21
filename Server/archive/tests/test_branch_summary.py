"""Multi-branch summary (v87.11): URL rules, answer checks, counts-only privacy, wiring. No network, no MySQL.
Run: python tests/test_branch_summary.py
"""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import branch_view as BV

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

def refused(fn):
    try:
        fn(); return False
    except BV.BranchError:
        return True

ok(BV.validate_branch_url('https://branch.example.com/') == 'https://branch.example.com', 'https address is accepted, trailing slash removed')
ok(BV.validate_branch_url('http://192.168.1.20:5000') == 'http://192.168.1.20:5000', 'plain http on a LAN address is accepted')
ok(BV.validate_branch_url('http://localhost:5000') == 'http://localhost:5000', 'localhost is accepted')
ok(refused(lambda: BV.validate_branch_url('http://branch.example.com')), 'plain http on the internet is refused')
ok(refused(lambda: BV.validate_branch_url('ftp://192.168.1.2')), 'non-web address is refused')
ok(refused(lambda: BV.validate_branch_url('')), 'empty address is refused')
ok(refused(lambda: BV.validate_branch_url('https://')), 'address with no host is refused')

good = {'data': {f: 3 for f in BV.FIELDS}}
ok(BV.parse_summary(good) == {f: 3 for f in BV.FIELDS}, 'a good answer is read')
ok(refused(lambda: BV.parse_summary({'data': {}})), 'a missing number is refused')
bad = {'data': {f: 3 for f in BV.FIELDS}}; bad['data']['low_stock_items'] = -1
ok(refused(lambda: BV.parse_summary(bad)), 'a negative number is refused')
bad2 = {'data': {f: 'many' for f in BV.FIELDS}}
ok(refused(lambda: BV.parse_summary(bad2)), 'text instead of a number is refused')
ok(refused(lambda: BV.parse_summary(['not', 'a', 'dict'])), 'a list answer is refused')
ok(refused(lambda: BV.fetch_summary('https://branch.example.com', '')), 'a fetch without a token is refused before any network call')
ok(refused(lambda: BV.fetch_summary('http://branch.example.com', 'tok')), 'a fetch to plain internet http is refused before any network call')

src = read('pharmacy/services/branch_view.py')
ok('FIELDS = (' in src and 'medicine' not in src.split('FIELDS = (')[1].split(')')[0].lower(), 'the shared fields are numbers only')
ok('name' not in src.split('def summary_counts')[1].lower().replace('month', ''), 'the summary query selects no names')
api = read('pharmacy/routes/api.py')
ok("@app.route('/api/v1/branch/summary')" in api and "@api_required('Admin', 'Pharmacist')" in api, 'the branch API needs a token (Admin or Pharmacist)')
ok(api.split("def api_branch_summary")[1].count('name') == 0, 'the branch API returns counts only')
bsrc = read('pharmacy/routes/branches.py')
ok("@role_required('Admin')" in bsrc and bsrc.count("@role_required('Admin')") == 2, 'the branch page and save are Admin only')
ok("audit(cur, 'branch.save'" in bsrc and 'the token is never logged' in bsrc, 'saving is logged, the token is not')
ok("if not token:\n            token = current['branch_token']" in bsrc, 'an empty token box keeps the saved token')
ok('type="password"' in read('templates/branches.html'), 'token box hides its text')
ok("'branches'" in read('templates/base.html') + read('pharmacy/routes/hubs.py'), 'Branch Summary link is in the sidebar')

import py_compile
for f in ['pharmacy/services/branch_view.py', 'pharmacy/routes/branches.py', 'pharmacy/routes/api.py']:
    try:
        py_compile.compile(os.path.join(ROOT, f), doraise=True); ok(True, f + ' compiles')
    except py_compile.PyCompileError as e:
        ok(False, f + ' compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
