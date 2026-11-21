"""v75: camera barcode scan falls back to ZXing where BarcodeDetector is missing. Source checks. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
js = open(_os.path.join(ROOT, 'static', 'js', 'scanner.js'), encoding='utf-8').read()
base = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
sw = open(_os.path.join(ROOT, 'static', 'js', 'sw.js'), encoding='utf-8').read()
ok('cdn.jsdelivr.net/npm/@zxing/library@0.21.3/' in js, 'ZXing loads from jsdelivr with an exact version')
ok('@zxing/library@latest' not in js and 'zxing/library@0.21' in js, 'no unpinned ZXing version')
ok('BrowserMultiFormatReader' in js and 'decodeFromVideoElement' in js, 'fallback decodes frames from the video')
ok('if (nativeSupported())' in js and 'BarcodeDetector' in js, 'native detector is still used first where it exists')
ok('loadZxing()' in js and "document.head.appendChild(s)" in js, 'ZXing is loaded only when needed, once')
ok("if (/zxing/.test(" in js, 'a ZXing load failure shows a clear message')
ok('function found(value)' in js and 'same barcode again' in js, 'both decoders share one duplicate check')
ok('barcode reader could not load' in js.lower() or 'Barcode reader could not load' in js, 'user sees what to do when the reader cannot load')
ok("scanner.js') }}?v=32" in base, 'base.html loads the new scanner version')
ok("const CACHE = 'medigen-static-v5';" in sw, 'service worker cache is bumped so phones get the new file')
ok('MediScan.open' in js and 'fillFrom' in js and 'supported:' in js, 'public API (open, fillFrom, supported) is unchanged')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
