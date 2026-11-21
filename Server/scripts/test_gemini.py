"""Quick check: is your Gemini key in .env working?

Run from the project folder:
    python scripts/test_gemini.py
Reads GEMINI_API_KEY and GEMINI_MODEL from .env. Prints the answer or the error (never the key).
    python scripts/test_gemini.py --list   -> shows the model names your key can use.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

from config import Config                      # reads .env
from pharmacy.ai_client import ask_gemini

if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY.startswith('PASTE_'):
    raise SystemExit('Please set GEMINI_API_KEY in .env first.')

if '--list' in sys.argv:
    # Shows which model names THIS key can use. Run: python scripts/test_gemini.py --list
    import json, urllib.request, urllib.error
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models',
                                 headers={'x-goog-api-key': Config.GEMINI_API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            models = json.loads(resp.read().decode('utf-8')).get('models', [])
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Could not list models: HTTP {e.code}')
    print('Models your key can use for text answers:')
    for m in models:
        if 'generateContent' in m.get('supportedGenerationMethods', []):
            print('  ' + m['name'].replace('models/', ''))
    raise SystemExit(0)

Config.AI_ENABLED = True
print('Model used:', Config.GEMINI_MODEL)
text, why = ask_gemini('Hello! Introduce yourself as MediGen AI Pharmacy Assistant.')
if text:
    print('MEDIGEN AI RESPONSE:')
    print(text)
else:
    print('Gemini API Error:', why)
    if why and why.startswith('http_'):
        # Show Google's own explanation (the key is hidden)
        import json, urllib.request, urllib.error
        from pharmacy.ai_client import GEMINI_URL
        body = json.dumps({'contents': [{'role': 'user', 'parts': [{'text': 'hi'}]}]}).encode('utf-8')
        req = urllib.request.Request(GEMINI_URL.format(model=Config.GEMINI_MODEL), data=body, method='POST',
                                     headers={'content-type': 'application/json', 'x-goog-api-key': Config.GEMINI_API_KEY})
        try:
            urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8', 'replace').replace(Config.GEMINI_API_KEY, '***')
            print('Google says:', detail[:400])
    print('Tip: http_400 or http_403 = key wrong or not enabled; http_429 = limit reached; unavailable = no internet.')
