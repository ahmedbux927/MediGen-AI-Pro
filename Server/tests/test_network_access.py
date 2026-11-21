"""v79: which networks may open the app (ALLOWED_NETWORKS). Pure checks + wiring. No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services.net_access import parse_networks as P, is_allowed as A
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

nets, bad = P('192.168.0.0/16, 100.64.0.0/10')
ok(len(nets) == 2 and not bad, 'two networks are read')
nets2, bad2 = P('192.168.0.0/16, junk, 10.0.0.0/8')
ok(bad2 == ['junk'] and len(nets2) == 2, 'a bad entry is reported and the good ones still work')
ok(A('192.168.1.20', nets), 'a shop WiFi address is allowed')
ok(A('100.100.5.5', nets), 'a VPN address is allowed')
ok(not A('8.8.8.8', nets), 'an address outside the list is refused')
ok(not A('203.0.113.9', nets), 'a public internet address is refused when a list is set')
ok(A('127.0.0.1', nets), 'this PC is always allowed')
ok(A('8.8.8.8', []), 'an empty list means no limit (old behaviour)')
ok(not A('not-an-ip', nets) and not A(None, nets), 'a broken address is refused when a list is set')
ok(P('')[0] == [] and P(None)[0] == [], 'empty setting is fine')

core = open(_os.path.join(ROOT, 'pharmacy', 'core.py'), encoding='utf-8').read()
ok('def _network_gate()' in core and "Config.ALLOWED_NETWORKS" in core, 'the gate reads the setting')
ok(core.index('def _network_gate()') < core.index('@app.before_request\ndef') + 40 and core.index('@app.before_request\ndef _network_gate') < core.index('@app.before_request\ndef', core.index('def _network_gate()') + 5), 'the network gate is the first before-request check, so it runs before login')
ok("'This app only accepts connections from the shop network or the owner VPN.', 403" in core, 'blocked visitors get a plain 403 message')
cfg = open(_os.path.join(ROOT, 'config.py'), encoding='utf-8').read()
ok("os.environ.get('ALLOWED_NETWORKS', '')" in cfg, 'config reads ALLOWED_NETWORKS')
env = open(_os.path.join(ROOT, '.env.example'), encoding='utf-8').read()
ok('ALLOWED_NETWORKS=' in env, 'the example .env shows the setting')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
