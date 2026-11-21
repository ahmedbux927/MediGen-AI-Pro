"""
Checks the internet-access helper (v32): start script and guide. Run: python tests/test_internet_access.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

bat = open(os.path.join(ROOT, 'scripts/start_internet.bat'), 'rb').read().decode('utf-8')
guide = open(os.path.join(ROOT, 'docs/INTERNET_ACCESS.md'), encoding='utf-8').read()
ok('cloudflared tunnel --url http://127.0.0.1:5000' in bat, 'script tunnels the local MediGen server')
ok('winget install --id Cloudflare.cloudflared' in bat, 'script tells the user how to install the tunnel tool')
ok('where cloudflared' in bat and 'exit /b 1' in bat, 'script stops with a clear message if the tool is missing')
ok('\r\n' in bat and '\n' not in bat.replace('\r\n', ''), 'batch file uses Windows line endings')
ok('C:\\Users' not in bat, 'script has no personal paths')
ok('HTTPS_ONLY=1' in guide and 'trycloudflare.com' in guide, 'guide covers the https cookie setting and the address')
ok('changes every time' in guide, 'guide warns that the quick address changes')

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
