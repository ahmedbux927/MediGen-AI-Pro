"""Frontend freeze check (backend track).

The backend work must not change anything the user sees. This test compares the checksums of
templates/ and static/ with tests/frontend_manifest.json (recorded on 23 Oct 2026, v49 start).
If a backend change touches a page or a stylesheet, this test fails.

Only when the frontend is changed on purpose: python tests/test_backend_freeze.py --write
Run: python tests/test_backend_freeze.py
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
MANIFEST = os.path.join(HERE, 'frontend_manifest.json')
FOLDERS = ('templates', 'static')
SKIP_PARTS = ('profiles',)          # user profile pictures change at run time, they are not code

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def snapshot():
    out = {}
    for folder in FOLDERS:
        base = os.path.join(ROOT, folder)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_PARTS and d != '__pycache__')
            for name in sorted(filenames):
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, ROOT).replace(os.sep, '/')
                with open(full, 'rb') as fh:
                    out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out

if '--write' in sys.argv:
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(snapshot(), fh, indent=1, sort_keys=True)
    print('manifest written:', MANIFEST)
    sys.exit(0)

recorded = json.load(open(MANIFEST, encoding='utf-8'))
now = snapshot()
changed = sorted(p for p in recorded if now.get(p) != recorded[p])
added = sorted(p for p in now if p not in recorded)
removed = sorted(p for p in recorded if p not in now)
ok(len(recorded) >= 40, f'manifest covers the frontend ({len(recorded)} files)')
ok(not changed, 'no template or static file changed' + (f' (changed: {changed[:5]})' if changed else ''))
ok(not removed, 'no template or static file removed' + (f' (removed: {removed[:5]})' if removed else ''))
ok(not added, 'no new template or static file added' + (f' (added: {added[:5]})' if added else ''))
print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
