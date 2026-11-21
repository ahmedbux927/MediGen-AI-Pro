"""
Chart style checks (v24): every chart uses static/js/charts.js, draws when visible,
has the right animation options, and respects reduced motion.
Runs the real JavaScript in node with a small fake Chart.js, so no browser or CDN is needed.
Run: python tests/test_charts_js.py
"""
import json, os, re, shutil, subprocess, sys
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
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()

js = read('static/js/charts.js')
dash = read('templates/dashboard.html')
rep = read('templates/reports.html')
ok('js/dashboard.js' in dash and 'MediCharts.' not in dash, 'dashboard charts live in dashboard.js (gradient area and sparkline)')
ok('MediCharts.revenueLine(' in rep, 'reports uses the shared revenue line')
ok('new Chart(' not in dash, 'no chart code left inline in the dashboard')
ok('new Chart(' not in rep, 'no chart code left inline in reports')
ok('js/charts.js' in rep, 'reports loads charts.js')
ok("'/static/js/charts.js'" in read('static/js/sw.js'), 'charts.js is cached for offline use')
ok('prefers-reduced-motion' in js and 'animation: false' not in js.replace('animation: reduced() ? false', ''), 'reduced motion turns animation off')
ok('IntersectionObserver' in js, 'charts start drawing when they are on screen')
ok('createLinearGradient' in js, 'bars and area use gradients')
ok('borderRadius: 10' in js and 'cutout' in js and 'animateRotate: true' in js, 'bars have rounded tops; doughnut sweeps in')
ok('drawInAnimation' in js and 'getPixelForValue(0)' in js, 'revenue line draws in point by point')

if shutil.which('node'):
    harness = r'''
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const made = [];
function FakeChart(canvas, cfg) { this.cfg = cfg; this.canvas = canvas; made.push(this); }
FakeChart.defaults = { font: {}, color: '' };
const els = {};
function canvas(id) { return els[id] || (els[id] = { id, style: {}, parentNode: { insertBefore(){} }, getContext(){ return {}; }, closest(){ return null; } }); }
global.Chart = FakeChart;
global.document = { getElementById: canvas, createElement(){ return { style:{}, classList:{toggle(){}}, setAttribute(){}, addEventListener(){}, querySelector(){ return null; } }; } };
global.window = global;
global.matchMedia = () => ({ matches: process.env.REDUCED === '1' });
eval(src);
const M = global.MediCharts;
M.weekBars('salesChart', ['a','b'], [0, 0]);
M.weekBars('salesChart2', ['a','b'], [5, 7]);
M.topDoughnut('medicinesChart', ['x','y'], [3, 4]);
M.revenueLine('revenueChart', ['d1','d2','d3'], [10, 0, 30]);
console.log(JSON.stringify(made.map(c => ({ type: c.cfg.type, anim: c.cfg.options.animation === false ? 'off' : 'on', data: c.cfg.data.datasets[0].data }))));
'''
    hp = os.path.join(ROOT, 'scratchpad_charts_harness.js')
    import tempfile
    d = tempfile.mkdtemp()
    hp = os.path.join(d, 'harness.js')
    open(hp, 'w', encoding='utf-8').write(harness)
    cp = os.path.join(ROOT, 'static', 'js', 'charts.js')
    def run(env):
        r = subprocess.run(['node', hp, cp], capture_output=True, text=True, env=dict(os.environ, **env))
        return r
    r = run({'REDUCED': '0'})
    ok(r.returncode == 0, 'charts.js runs without errors (fake Chart.js)')
    if r.returncode == 0:
        out = json.loads(r.stdout.strip().splitlines()[-1])
        ok(len(out) == 3, 'zero-sales week and empty sales show a note instead of a chart (3 charts drawn)')
        ok(out[0]['type'] == 'bar' and out[1]['type'] == 'doughnut' and out[2]['type'] == 'line', 'bar, doughnut and line are created in order')
        ok(out[2]['data'] == [10, 0, 30], 'line keeps real values, including a zero day')
        ok(all(c['anim'] == 'on' for c in out), 'animations are on when motion is allowed')
    r2 = run({'REDUCED': '1'})
    if r2.returncode == 0:
        out2 = json.loads(r2.stdout.strip().splitlines()[-1])
        ok(all(c['anim'] == 'off' for c in out2), 'with reduce-motion on, every chart is drawn without animation')
    else:
        ok(False, 'charts.js runs with reduce-motion on')
    shutil.rmtree(d, ignore_errors=True)
else:
    print('SKIP node not installed: behaviour checks skipped')

print(f'\n{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
