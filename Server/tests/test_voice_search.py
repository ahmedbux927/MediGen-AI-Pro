"""Static checks for voice search on the medicine search boxes (v86.51). Run through tests/run_all.py or directly."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

js = read('static/js/voice-search.js')
css = read('static/css/medicine-look.css')
med = read('templates/medicines.html')
sec = read('templates/products.html')
ok('isSecureContext' in js, 'mic is only offered in a secure context (localhost or https)')
ok("rec.lang = 'en-IN'" in js, 'speech language set to en-IN')
ok("dispatchEvent(new Event('input'" in js, 'spoken text fires the live filter')
ok('btn.hidden = true' in js, 'button hidden when the browser cannot listen')
ok('.med-mic' in css and '.med-mic[hidden]' in css, 'mic button styles exist')
for name, t, fn in (('medicines', med, 'medFilter'), ('sections', sec, 'secFilter')):
    ok('voice-search.js' in t, f'{name} page loads voice-search.js')
    ok('data-voice-for="searchInput"' in t, f'{name} page has the mic button')
    ok('has-mic' in t and f'oninput="{fn}(this.value)"' in t, f'{name} search box still runs its live filter')

if __name__ == '__main__':
    bad = [m for m, c in RESULTS if not c]
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(bad)} passed, {len(bad)} failed')
