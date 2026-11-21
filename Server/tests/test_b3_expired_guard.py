"""B3 guard: expired batches are never picked for a sale, and the check is in the one place that picks batches.
Source check (no MySQL). If someone removes the expiry filter, this test fails."""
import os as _os, re
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

src = open(_os.path.join(ROOT, 'pharmacy', 'services', 'sales.py'), encoding='utf-8').read()
start = src.index('def pick_batches(')
end = src.index('\ndef ', start + 10)
body = src[start:end]
ok('expiry_date >= CURDATE()' in body, 'pick_batches filters out expired batches (expiry_date >= CURDATE())')
ok('quantity > 0' in body, 'pick_batches ignores batches with zero quantity')
ok(re.search(r'ORDER BY expiry_date ASC', body) is not None, 'oldest expiry is sold first (FIFO by expiry)')
ok("Expired batches cannot be sold" in body, 'a clear message is shown when only expired stock is left')
ok(src.count('expiry_date >= CURDATE()') >= 1, 'expiry rule is present in the sales service')

print('\n'.join(('PASS ' if c else 'FAIL ') + m for m, c in RESULTS))
