"""Motion layer and soft sound (v87.14). Static checks, no browser or MySQL needed.
Run: python tests/test_motion.py
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
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

css = read('static/css/motion.css')
js = read('static/js/motion.js')
base = read('templates/base.html')

bundle = read('static/css/app.css')
ok('css/app.css' in base and '===== motion.css =====' in bundle and 'js/motion.js' in base, 'motion files are wired into base.html (via the app.css bundle)')
ok(bundle.index('===== motion.css =====') > bundle.index('===== page-look.css ====='), 'motion.css loads after the other styles (bundle order)')
ok('prefers-reduced-motion: reduce' in css, 'reduced-motion users get no movement')
ok('transform' in css or 'opacity' in css, 'motion uses transform and opacity (cheap)')
ok('sound: false' in js and 'localStorage' in js, 'sound is off by default and stored per device')
ok('--mg-speed' in css and '--mg-strength' in css and 'mg-panel' in css, 'speed and strength are live settings in CSS')
ok('bi-sliders' in js and 'cfg.volume' in js, 'panel has volume and the sound uses it')
ok('AudioContext' in js and 'fetch(' not in js and 'new Audio(' not in js, 'sound is synthesized, no audio file')
ok('sideNav' in js and 'data-ai-open' in js, 'page fade only for sidebar links; assistant link skipped')
ok("'sales'" not in css and 'pos-' not in css and 'new-sale' not in css, 'no motion rules target the POS screen')
ok('Build v{{ app_version }}' in read('templates/medicines.html'), 'build marker is v87.14')

print('\n%d passed, %d failed' % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
