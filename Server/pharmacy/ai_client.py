"""Gemini API helper for the chatbot (v100.00: Gemini is the only provider, owner decision).

Used ONLY when the offline engine does not understand a question and AI is switched on.
Privacy: only the typed question (max 300 characters) and a fixed system prompt are sent.
No customer, patient, sales or stock data is sent. API keys come from the Settings
page (app_settings) or from .env, and are never printed, logged or returned to the browser.
"""
import json
import logging
import urllib.error
import urllib.request

from config import Config

MAX_QUESTION = 300
MAX_ANSWER_TOKENS = 400

# v89.00: condensed program knowledge, so the ONLINE AI assistant knows MediGen AI Pro itself.
# The full manual is docs/PROGRAM_MANUAL.md. Only this summary is sent to the provider - never shop data.
PROGRAM_KNOWLEDGE = (
    "Program map of MediGen AI Pro (pharmacy ERP/POS for one shop, version 100.00): "
    "The built-in assistant also carries an offline knowledge base of 116 common medicines "
    "(uses, side effects, warnings) in medicine_knowledge.py, so medicine questions are answered even without internet. "
    "Dashboard: today's sales and profit, low stock, expiring batches (30/60/90 days), each card links to a filtered list. "
    "Catalog/Products: product sections (Medicines, Syrups, Creams, Drips/Injections, Bandages), categories, import from CSV/PDF/Word. "
    "Medicines: add/edit/delete (soft delete, Admin confirms), barcode, shelf location, reorder level, bulk edit. "
    "Batches: FIFO selling, expiry tracking, write-off of expired stock. "
    "New Sale (POS): search or scan barcode, discount percent or rupees (cashier limit applies), tax, udhaar credit needs a customer, "
    "receipts A4 and 80mm, repeat submit with the same client id never saves twice. "
    "Sales: list, payments, returns (stock goes back to the same batch), receipts. "
    "Purchases: purchase orders and goods receiving create batches and stock; suppliers and supplier ledger. "
    "Prescriptions (Rx): records with photo upload and scan review, dispense from Rx. "
    "Customers: records, dues/udhaar. Expenses and cash drawer: daily cash in/out and closing. "
    "Reports (Admin): sales, profit, stock, expiry, tax and purchases, export CSV (Excel-ready), Excel, PDF, Word. "
    "Data Quality page: duplicate barcodes, price 0, stock mismatches. "
    "Users and roles: Admin, Pharmacist, Cashier; login lockout after repeated wrong passwords; Remember me keeps a PC signed in for 30 days. "
    "Settings: shop name, phone, receipt footer, tax rate, cashier discount limit. "
    "Backup: python scripts/backup_db.py runs a real mysqldump; a failed backup never claims success. "
    "Start: START_MEDIGEN.bat starts the server (waitress) and opens the workbench; STOP_MEDIGEN.bat stops it. "
    "Forgot password: python reset_password.py on the shop PC."
)

SYSTEM_PROMPT = (
    "You are MediGen AI, a helpful assistant for a small pharmacy in Pakistan. "
    "Answer briefly, in bullet points. Reply in the same language the user writes in "
    "(English or Roman Urdu). Do not diagnose or prescribe. For any dosage, interaction or "
    "clinical question, end with: 'Please verify with a licensed pharmacist.' "
    "You cannot see this shop's live stock or sales. If the user needs those numbers, "
    "suggest a short question such as 'Panadol stock' or 'Today sales'."
    + PROGRAM_KNOWLEDGE
)

log = logging.getLogger('medigen.ai')

# v88.00: EVERY AI answer shown to a user must carry this note (enforced in pharmacy/lib.py _chat_reply).
PHARMACIST_NOTE = '*AI answer. Please verify with a licensed pharmacist before any clinical decision.*'


def ensure_pharmacist_note(text):
    """Return the text with the pharmacist-check note appended, unless it is already there."""
    if not text:
        return text
    if 'verify with a licensed pharmacist' in text:
        return text
    return text.rstrip() + '\n\n' + PHARMACIST_NOTE


def _settings_key(setting_name):
    """A key saved on the Settings page (app_settings table) wins over .env.
    Lazy import: pharmacy.lib imports this module, so importing it at the top
    would be circular. Never raises - any problem means 'no key from settings'."""
    try:
        from pharmacy.lib import get_setting
        return (get_setting(setting_name) or '').strip()
    except Exception:
        return ''


def _gemini_key():
    """The Gemini API key: Settings page (app_settings) first, then .env."""
    return _settings_key('gemini_api_key') or Config.GEMINI_API_KEY


def ai_enabled():
    """True only when AI is switched on AND a Gemini key is saved
    (on the Settings page, or in .env)."""
    return bool(Config.AI_ENABLED and _gemini_key())


def ai_status():
    """(online, provider_label) for the chat header. Gemini is the only provider."""
    if not Config.AI_ENABLED:
        return False, ''
    return (True, 'Gemini') if _gemini_key() else (False, '')


def ask_ai(question):
    """Ask Gemini. Returns (text, None) or (None, reason). Never raises."""
    if not ai_enabled():
        return None, 'disabled'
    return ask_gemini(question)


def friendly_reason(why):
    """v92.00: turn an ask_* reason code into one plain sentence for the user."""
    if not why:
        return 'unknown error'
    if why == 'unavailable':
        return "the provider could not be reached (check this PC's internet connection)"
    if why == 'empty_reply':
        return 'the provider replied with an empty answer'
    if why == 'disabled':
        return 'no working API key is saved'
    if why.startswith('http_'):
        code = why[5:]
        if code in ('401', '403'):
            return f'the API key was refused (HTTP {code}) - the key is not valid for this provider'
        if code == '400':
            return 'the provider rejected the request (HTTP 400) - usually an invalid API key'
        if code == '404':
            return 'the AI model was not found for this key (HTTP 404)'
        if code == '429':
            return 'the provider rate limit was reached (HTTP 429) - try again in a minute'
        if code in ('500', '502', '503'):
            return f'the provider is having problems (HTTP {code}) - try again later'
        return f'the provider returned HTTP {code}'
    return why


def test_provider(prov):
    """One tiny live call with the saved Gemini key, for the Settings
    'Test connection' button. Returns (ok, message). Never exposes the key."""
    import time
    if prov != 'gemini':
        return False, 'Unknown provider.'
    if not _gemini_key():
        return False, 'No Gemini key is saved yet. Paste the key above, save, then test.'
    t0 = time.time()
    text, why = ask_gemini('Reply with exactly one word: OK')
    secs = time.time() - t0
    if text:
        return True, f'Connected - Gemini answered in {secs:.1f} seconds. The AI Assistant can use Gemini now.'
    return False, f'Gemini did not answer: {friendly_reason(why)}.'


GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'


def ask_gemini(question):
    """Google Gemini generateContent. Tries the main model, then fallbacks if busy or over limit.
    Returns (text, None) or (None, reason). Never raises."""
    key = _gemini_key()
    if not (Config.AI_ENABLED and key):
        return None, 'disabled'
    text = (question or '').strip()[:MAX_QUESTION]
    if not text:
        return None, 'empty'
    body = json.dumps({
        'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': [{'role': 'user', 'parts': [{'text': text}]}],
        'generationConfig': {'maxOutputTokens': MAX_ANSWER_TOKENS},
    }).encode('utf-8')
    models = [Config.GEMINI_MODEL] + [x for x in Config.GEMINI_FALLBACK_MODELS if x != Config.GEMINI_MODEL]
    reason = 'unavailable'
    for model in models:
        req = urllib.request.Request(GEMINI_URL.format(model=model), data=body, method='POST', headers={
            'content-type': 'application/json',
            'x-goog-api-key': key,
        })
        try:
            with urllib.request.urlopen(req, timeout=Config.AI_TIMEOUT) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            parts = (((data.get('candidates') or [{}])[0].get('content') or {}).get('parts')) or []
            reply = '\n'.join(p.get('text', '') for p in parts if isinstance(p, dict)).strip()
            return (reply, None) if reply else (None, 'empty_reply')
        except urllib.error.HTTPError as e:
            log.warning('Gemini model %s returned HTTP %s', model, e.code)   # status only, never the key
            reason = f'http_{e.code}'
            if e.code in (429, 503):
                continue                      # busy or over limit: try the next model
            return None, reason               # key/model/request problem: no point retrying
        except Exception as e:
            log.warning('Gemini API unavailable (%s)', type(e).__name__)
            return None, 'unavailable'
    return None, reason


