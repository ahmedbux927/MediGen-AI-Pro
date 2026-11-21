"""v54 error codes: the user sees 'Error E-xxx' and the Admin finds it in the log. No database needed.
Run: python tests/test_error_codes.py
"""
import os, sys, types
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = None
m.MySQL = MySQL
sys.modules['flask_mysqldb'] = m

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

import app as A
from pharmacy.lib import ERROR_CODES, flash_unexpected
from flask import get_flashed_messages

codes = list(ERROR_CODES.values())
ok(len(codes) == len(set(codes)), 'every error code is unique')
ok(all(c.startswith('E-') and c[2:].isdigit() for c in codes), 'codes look like E-123')
ok(ERROR_CODES['medicine_add'] == 'E-102', 'add medicine error is E-102')
ok(ERROR_CODES['api_checkout'] == 'E-501', 'POS checkout error is E-501')

with A.app.test_request_context('/'):
    flash_unexpected('Medicine could not be added.', code=ERROR_CODES['medicine_add'])
    msgs = get_flashed_messages()
ok(msgs and 'Error E-102.' in msgs[0] and 'check the log' in msgs[0], 'message shows the code and points to the log')

with A.app.test_request_context('/'):
    flash_unexpected('Something went wrong.')
    msgs = get_flashed_messages()
ok(msgs and 'Error E-' not in msgs[0], 'without a code the message has no code')

print(f'\nTOTAL {PASS + FAIL}  PASS {PASS}  FAIL {FAIL}')
sys.exit(1 if FAIL else 0)
