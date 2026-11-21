"""Checks for the friendly 'database is down' message (v86.52). Run through tests/run_all.py or directly.
The classifier is pulled out of pharmacy/lib.py with ast, so the test does not need the app or a database."""
import ast, os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

src = open(_os.path.join(ROOT, 'pharmacy', 'lib.py'), encoding='utf-8').read()
tree = ast.parse(src)
ns = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'DB_DOWN_CODES' for t in node.targets):
        exec(compile(ast.Module([node], []), 'lib', 'exec'), ns)
    if isinstance(node, ast.FunctionDef) and node.name == 'is_db_down':
        exec(compile(ast.Module([node], []), 'lib', 'exec'), ns)
is_db_down = ns.get('is_db_down')

class OperationalError(Exception): pass
class InterfaceError(Exception): pass
class ProgrammingError(Exception): pass

ok(is_db_down is not None, 'classifier found in lib.py')
if is_db_down:
    ok(is_db_down(OperationalError(2003, "Can't connect to MySQL server")), 'error 2003 (cannot connect) is treated as database down')
    ok(is_db_down(OperationalError(2006, 'MySQL server has gone away')), 'error 2006 (server gone away) is treated as database down')
    ok(is_db_down(InterfaceError(2013, 'Lost connection')), 'error 2013 (lost connection) is treated as database down')
    ok(not is_db_down(OperationalError(1205, 'Lock wait timeout')), 'other MySQL errors are not treated as database down')
    ok(not is_db_down(ProgrammingError(2003, 'x')), 'only connection error classes count')
    ok(not is_db_down(ValueError('boom')), 'ordinary Python errors are not treated as database down')
    ok(not is_db_down(Exception()), 'errors with no args do not crash the check')
ok("if is_db_down(exc):" in src and "503" in src, 'guarded shows the message and returns 503')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
