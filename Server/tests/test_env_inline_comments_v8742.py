"""v87.43: .env reader must ignore inline comments (APP_HOST=0.0.0.0   # note -> 0.0.0.0).
Mock suite: no MySQL, no network. Run through tests/run_all.py."""
import os, sys, tempfile

ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
import config  # noqa: E402

FAILS = []


def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond:
        FAILS.append(msg)


def load(text, keys):
    for k in keys:
        os.environ.pop(k, None)
    fd, path = tempfile.mkstemp(suffix='.env')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    try:
        config._load_env(path)
    finally:
        os.remove(path)
    return {k: os.environ.get(k) for k in keys}


keys = ['T42_HOST', 'T42_PROVIDER', 'T42_QUOTED', 'T42_PLAIN', 'T42_PATH', 'T42_EMPTY', 'T42_HASH']
got = load(
    'T42_HOST=0.0.0.0            # listen on WiFi\n'
    'T42_PROVIDER=gemini   # primary\n'
    'T42_QUOTED="abc # not a comment"\n'
    'T42_PLAIN=plain\n'
    'T42_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe\n'
    'T42_EMPTY=\n'
    'T42_HASH=ab#cd\n',
    keys)
ok(got['T42_HOST'] == '0.0.0.0', 'inline comment after IP is removed')
ok(got['T42_PROVIDER'] == 'gemini', 'inline comment after provider name is removed')
ok(got['T42_QUOTED'] == 'abc # not a comment', 'quoted value keeps its # text')
ok(got['T42_PLAIN'] == 'plain', 'plain value unchanged')
ok(got['T42_PATH'] == 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe', 'Windows path with spaces unchanged')
ok(got['T42_EMPTY'] == '', 'empty value stays empty')
ok(got['T42_HASH'] == 'ab#cd', 'hash without a leading space is kept')

for k in keys:
    os.environ.pop(k, None)

if FAILS:
    print('FAILED: %d' % len(FAILS))
    sys.exit(1)
