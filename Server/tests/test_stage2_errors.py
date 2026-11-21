"""Stage 2 (Master Prompt v4): typed errors are wired, no bare/silent excepts.

- pharmacy/errors.py classes carry a safe user_message and a log-only detail.
- A Flask handler for MediGenError is registered (friendly page/JSON, never a 500 stack page).
- BillError (sales) is a MediGenError AND still a ValueError for old catch sites.
- Source scan: no bare `except:` and no silent `except ...: pass` in pharmacy/.
No MySQL needed.
"""
import ast
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


from pharmacy import errors as E  # noqa: E402

for name in ('MediGenError', 'ValidationError', 'NotFoundError', 'PermissionDenied',
             'StockError', 'ConflictError', 'PaymentError', 'ExternalServiceError', 'DatabaseError'):
    ok(hasattr(E, name), f'typed error class exists: {name}')

err = E.StockError()
ok('stock' in err.user_message.lower() and err.detail, 'StockError has a safe default user_message and detail')
err2 = E.ValidationError('Quantity must be more than zero', detail='qty=-3 field=quantity')
ok(err2.user_message == 'Quantity must be more than zero' and err2.detail == 'qty=-3 field=quantity',
   'user_message and detail stay separate')

from pharmacy.services.sales import BillError  # noqa: E402
ok(issubclass(BillError, E.MediGenError) and issubclass(BillError, ValueError),
   'BillError is both a MediGenError and a ValueError (old catch sites keep working)')
be = BillError('Insufficient stock for Panadol')
ok(be.user_message == 'Insufficient stock for Panadol', 'BillError message flows into user_message')

# handler registered on the real app
from pharmacy.routes import errors as route_errors  # noqa: E402,F401  (import registers the handlers)
from pharmacy.core import app  # noqa: E402
spec = app.error_handler_spec.get(None, {})
ok(E.MediGenError in spec.get(None, {}) or any(E.MediGenError in v for v in spec.values()),
   'a Flask error handler is registered for MediGenError')

# source scan: no bare except, no silent pass in pharmacy/
bad = []
pkg = _os.path.join(ROOT, 'pharmacy')
for dirpath, _dirs, files in _os.walk(pkg):
    for fn in files:
        if not fn.endswith('.py'):
            continue
        path = _os.path.join(dirpath, fn)
        tree = ast.parse(open(path, encoding='utf-8', errors='ignore').read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    bad.append(f'{fn}:{node.lineno} bare except')
                elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    bad.append(f'{fn}:{node.lineno} silent pass')
ok(not bad, 'no bare except and no silent except-pass in pharmacy/' + (f' (found: {bad[:3]})' if bad else ''))

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
