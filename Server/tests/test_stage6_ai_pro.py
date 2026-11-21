"""Stage 6 (Master Prompt v4): AI Pro guardrails.

- Per-user rate limit on the chat endpoint (20 questions/minute).
- A 10-minute answer cache, never used for live-data questions.
- The daily AI summary is off by default, gated by a Settings toggle,
  cached per day, and its prompt is built ONLY from aggregate numbers.
No MySQL and no network needed.
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


from pharmacy.services import ai_pro as AIP  # noqa: E402

lim = AIP.RateLimiter()
ok(all(lim.allow(7, now=1000.0 + i * 0.1) for i in range(20)), 'rate limiter allows 20 questions in the window')
ok(not lim.allow(7, now=1002.5), 'the 21st question inside a minute is blocked')
ok(lim.allow(8, now=1002.5), 'another user is not affected')
ok(lim.allow(7, now=1061.0), 'after the window passes, questions are allowed again')

cache = AIP.TTLCache()
cache.put(('u', 'panadol kis liye hai'), ('answer', []), now=500.0)
ok(cache.get(('u', 'panadol kis liye hai'), now=900.0) == ('answer', []), 'cache returns the answer within 10 minutes')
ok(cache.get(('u', 'panadol kis liye hai'), now=1200.0) is None, 'cache entry expires after 10 minutes')
ok(cache.get(('u', 'never asked'), now=900.0) is None, 'cache miss returns None')

prompt = AIP.build_summary_prompt({'sales_today': 12500, 'bills_today': 34, 'low_stock': 6,
                                   'expiring_30d': 3, 'dues_total': 4200})
ok('12500' in prompt and '34' in prompt and '4200' in prompt, 'summary prompt carries the aggregate numbers')
ok('phone' not in prompt.lower() and 'patient' in prompt.lower(),
   'summary prompt states it holds no patient information and asks for none')

chat = read('pharmacy/routes/chatbot.py')
ok('_limiter.allow' in chat and '429' in chat, 'chat endpoint enforces the rate limit (HTTP 429)')
ok('_answer_cache' in chat and 'live_words' in chat, 'chat endpoint caches answers but never live-data questions')

dash = read('pharmacy/routes/dashboard.py')
ok("get_setting('ai_daily_summary') == '1'" in dash, 'daily summary runs only when the owner turned it on')
ok('ai_summary_cache' in dash and 'build_summary_prompt' in dash,
   'daily summary is cached per day and built from aggregates only')
ok('ai_summary=ai_summary' in dash, 'dashboard receives the summary')

settings = read('pharmacy/routes/settings.py')
ok("request.form.get('ai_pane')" in settings and 'ai_daily_summary' in settings,
   'the summary toggle saves only from the AI pane (other panes cannot switch it off)')
tpl = read('templates/settings.html')
ok('name="ai_daily_summary"' in tpl, 'Settings AI pane has the daily summary checkbox')
ok('then OpenAI, then Claude' not in tpl, 'stale multi-provider copy removed from Settings (Gemini only)')
ok('Daily AI Summary' in read('templates/dashboard.html'), 'dashboard has the labelled AI summary card')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
