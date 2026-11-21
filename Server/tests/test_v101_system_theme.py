"""v101.01: the theme follows the system (OS light/dark) by default.

Modes: system (default), light, dark - cycled by the top-bar button and kept
per browser. The effective theme is always in data-theme (the CSS contract);
the login page starts from the same saved mode or the system setting.
"""
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


base = read('templates/base.html')
ok('prefers-color-scheme: dark' in base, 'base theme init reads the system preference')
ok('mgThemeMode' in base and "data-theme-mode" in base, 'theme mode (system/light/dark) is tracked on <html>')
ok("['system', 'light', 'dark']" in base, 'the toggle cycles system -> light -> dark')
ok('addEventListener' in base and "mode() === 'system'" in base, 'a live OS theme change updates the page in system mode')
ok("localStorage.getItem('mgTheme')" in base, 'an older saved mgTheme choice is still respected')

login_js = read('static/js/login.js')
ok('prefers-color-scheme: dark' in login_js and 'mgThemeMode' in login_js,
   'login page starts from the saved mode or the system setting')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
