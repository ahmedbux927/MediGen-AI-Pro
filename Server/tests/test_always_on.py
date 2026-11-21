"""
Checks the always-on server files (v28): auto-restart loop, hidden start at log on, power settings, guide.
Run: python tests/test_always_on.py
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

def read(rel):
    return open(os.path.join(ROOT, rel), 'rb').read().decode('utf-8')

loop = read('scripts/run_server.bat')
ok(':loop' in loop and 'goto loop' in loop, 'server launcher restarts in a loop')
ok('python app.py' in loop and 'logs\\server.log' in loop, 'server output is written to logs\\server.log')
ok('cd /d "%~dp0\\.."' in loop, 'launcher runs from the project folder (no hard-coded user path)')
vbs = read('scripts/run_server_hidden.vbs')
ok(', 0, False' in vbs and 'run_server.bat' in vbs, 'hidden start: window style 0, runs the loop launcher')
inst = read('scripts/install_always_on.bat')
ok('schtasks /Create /TN "MediGen Server"' in inst and '/SC ONLOGON' in inst, 'startup task is created at log on')
ok('standby-timeout-ac 0' in inst and 'LIDACTION 0' in inst, 'no sleep on AC and lid close does nothing')
ok('MySQL80' in inst, 'MySQL service is checked')
ok('C:\\Users' not in inst and 'ahmed' not in inst.lower(), 'installer has no personal paths')
ok(all('\r\n' in read(f) and '\n' not in read(f).replace('\r\n', '') for f in
       ['scripts/run_server.bat', 'scripts/install_always_on.bat']), 'batch files use Windows line endings')
guide = read('docs/ALWAYS_ON_SERVER.md')
ok('install_always_on.bat' in guide and 'UPS' in guide and 'Task Manager' in guide, 'guide covers setup, UPS and stopping the server')

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
