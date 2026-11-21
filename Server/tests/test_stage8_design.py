"""Stage 8 (Master Prompt v4): one design system.

base.html loads ONE generated bundle (static/css/app.css) instead of 13
stylesheets. The bundle is built by scripts/build_css.py from the part files
in the exact old cascade order (brand.css's @import hoisted to the top).
Also: a global double-submit guard for server-calling forms.
No MySQL needed.
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
ok("css/app.css" in base, 'base.html loads the single app.css bundle')
for old in ('css/classic.css', 'css/pages.css', 'css/brand.css', 'css/theme.css', 'css/shell-light.css',
            'css/page-look.css', 'css/motion.css', 'css/dashboard-pro.css', 'css/assistant.css',
            'css/mg-ui.css', 'css/v88-polish.css', 'css/v89-premium.css', 'css/v92-theme.css', 'css/v100-theme.css'):
    ok(old not in base, f'base.html no longer links {old} directly')

bundle = read('static/css/app.css')
ORDER = ['classic.css', 'pages.css', 'brand.css', 'theme.css', 'shell-light.css', 'page-look.css',
         'motion.css', 'dashboard-pro.css', 'assistant.css', 'mg-ui.css', 'v88-polish.css',
         'v89-premium.css', 'v92-theme.css', 'v100-theme.css']
pos = [bundle.index(f'===== {name} =====') for name in ORDER]
ok(pos == sorted(pos), 'app.css keeps the exact old cascade order for all 14 part files')
head = bundle[:bundle.index('===== classic.css =====')]
ok('@import' in head and 'Playfair' in head, "brand.css's Google Fonts @import is hoisted to the top of the bundle")
ok('build_css.py' in bundle[:300], 'app.css is marked as generated (do not edit by hand)')
ok(_os.path.exists(_os.path.join(ROOT, 'scripts', 'build_css.py')), 'scripts/build_css.py regenerates the bundle')

ok('submit-guard.js' in base, 'base.html loads the double-submit guard')
guard = read('static/js/submit-guard.js')
ok('data-no-guard' in guard and 'pageshow' in guard, 'guard skips opted-out forms and restores buttons from the back-cache')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
