"""Step 9c checks: Gemini as an optional chatbot provider. Mock network, no real API call."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, types, json, io, urllib.request, urllib.error
sys.path.insert(0, ROOT); _cwd = _os.getcwd(); _os.chdir(ROOT)
bc = types.ModuleType('bcrypt'); bc.gensalt = lambda *a, **k: b'x'
bc.hashpw = lambda p, s: b'h:' + p; bc.checkpw = lambda p, h: h == b'h:' + p
sys.modules['bcrypt'] = bc
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
m = types.ModuleType('flask_mysqldb')
class MySQL:
    def __init__(self, app): self.connection = None
m.MySQL = MySQL; sys.modules['flask_mysqldb'] = m
from config import Config
from pharmacy import ai_client as AI

FAKE = 'AIza-TEST-ONLY-0000'
class FakeResp:
    def __init__(self, payload): self._b = json.dumps(payload).encode('utf-8')
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False
cap = {}
def ok_gemini(req, timeout=None):
    cap['url'] = req.full_url; cap['headers'] = {k.lower(): v for k, v in req.header_items()}
    cap['body'] = json.loads(req.data.decode('utf-8'))
    return FakeResp({'candidates': [{'content': {'parts': [{'text': 'Paracetamol ke saath pani lein.'}]}}]})
def bad_400(req, timeout=None):
    raise urllib.error.HTTPError(req.full_url, 400, 'bad', {}, io.BytesIO(b'{}'))
def boom(req, timeout=None): raise urllib.error.URLError('offline')
real = urllib.request.urlopen

Config.AI_ENABLED = True; Config.AI_PROVIDER = 'gemini'; Config.GEMINI_API_KEY = FAKE
Config.GEMINI_MODEL = 'gemini-2.5-flash'; Config.OPENAI_API_KEY = ''; Config.CLAUDE_API_KEY = ''
ok(AI.ai_enabled() is True, 'Gemini provider with its key -> AI on')
Config.GEMINI_API_KEY = ''
ok(AI.ai_enabled() is False, 'Gemini provider without key -> AI off')
Config.GEMINI_API_KEY = FAKE

urllib.request.urlopen = ok_gemini
txt, why = AI.ask_ai('  Dawai kab leni hai?  ')
ok(txt == 'Paracetamol ke saath pani lein.' and why is None, 'Gemini reply text is returned')
ok(cap['url'] == 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent', 'calls the official Gemini endpoint over https')
ok(cap['headers'].get('x-goog-api-key') == FAKE, 'sends the key in the x-goog-api-key header')
ok(cap['body']['contents'][0]['parts'][0]['text'] == 'Dawai kab leni hai?', 'only the trimmed question is sent as content')
ok('systemInstruction' in cap['body'] and 'pharmacist' in cap['body']['systemInstruction']['parts'][0]['text'], 'pharmacy system prompt is sent')
ok(FAKE not in json.dumps(cap['body']), 'the key is never in the request body')
ok('Ahmed' not in json.dumps(cap['body']), 'no user or shop data in the request')

urllib.request.urlopen = bad_400
txt, why = AI.ask_ai('test')
ok(txt is None and why == 'http_400', 'bad Gemini key -> http_400, no crash')
ok(FAKE not in str(why), 'failure reason never has the key')
urllib.request.urlopen = boom
txt, why = AI.ask_ai('test')
ok(txt is None and why == 'unavailable', 'no internet -> unavailable, no crash')
urllib.request.urlopen = real


# ---- busy model (503) falls back to the next model ----
Config.GEMINI_API_KEY = FAKE; Config.GEMINI_MODEL = 'gemini-busy'; Config.GEMINI_FALLBACK_MODELS = ['gemini-backup']
tried = []
def busy_then_ok(req, timeout=None):
    tried.append(req.full_url.split('/models/')[1].split(':')[0])
    if 'gemini-busy' in req.full_url:
        raise urllib.error.HTTPError(req.full_url, 503, 'busy', {}, io.BytesIO(b'{}'))
    return FakeResp({'candidates': [{'content': {'parts': [{'text': 'Backup model ka jawab.'}]}}]})
urllib.request.urlopen = busy_then_ok
txt, why = AI.ask_gemini('test')
ok(txt == 'Backup model ka jawab.' and tried == ['gemini-busy', 'gemini-backup'], 'busy model (503) -> next model answers')
def bad_key(req, timeout=None):
    tried.append('x')
    raise urllib.error.HTTPError(req.full_url, 400, 'bad', {}, io.BytesIO(b'{}'))
tried.clear(); urllib.request.urlopen = bad_key
txt, why = AI.ask_gemini('test')
ok(txt is None and why == 'http_400' and len(tried) == 1, 'bad key (400) is not retried on other models')
urllib.request.urlopen = real
Config.GEMINI_MODEL = 'gemini-2.5-flash'; Config.GEMINI_FALLBACK_MODELS = ['gemini-2.5-flash-lite', 'gemini-2.5-flash']

Config.AI_PROVIDER = 'anthropic'; Config.GEMINI_API_KEY = ''
failed = [x for x, p in RESULTS if not p]
for msg, p in RESULTS: print(('PASS ' if p else 'FAIL ') + msg)
_os.chdir(_cwd)
print(f'\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed')
sys.exit(1 if failed else 0)
