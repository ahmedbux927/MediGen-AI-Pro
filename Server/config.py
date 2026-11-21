"""
MediGen AI Pro - settings.
All secrets live in the .env file (never inside app.py).
Works without any extra package: it has its own tiny .env reader.
"""
import os
import secrets

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))   # packaged .exe: files live next to the exe
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_env(path):
    """Read KEY=VALUE lines from .env into os.environ (real environment wins)."""
    if not os.path.exists(path):
        return False
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            value = value.strip()
            if value[:1] in ('"', "'"):
                value = value.strip('"').strip("'")          # quoted value: keep everything inside the quotes
            else:
                # v87.43: "APP_HOST=0.0.0.0   # comment" must give "0.0.0.0", not the whole line.
                # A space followed by # starts a comment. Put a value that really has " #" in quotes.
                value = value.split(' #', 1)[0].split('\t#', 1)[0].strip()
            os.environ.setdefault(key.strip(), value)
    return True


# Windows sometimes renames ".env" to "env" or ".env.txt" when it is downloaded, so we accept those too.
ENV_FILE = None
for _name in ('.env', 'env', '.env.txt', 'env.txt'):
    if _load_env(os.path.join(BASE_DIR, _name)):
        ENV_FILE = _name
        break


def _flag(name, default='0'):
    return os.environ.get(name, default).strip().lower() in ('1', 'true', 'yes', 'on')


class Config:
    APP_VERSION = '101.03'                    # v88.00: ONE version source - every page/endpoint reads this
    BASE_DIR = BASE_DIR                      # folder that holds .env, templates, static, backups
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)   # random if missing: logins reset on restart
    SECRET_KEY_GENERATED = not os.environ.get('SECRET_KEY')
    MYSQL_HOST = os.environ.get('DB_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('DB_PORT', '3306'))
    MYSQL_USER = os.environ.get('DB_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('DB_PASSWORD', '')
    MYSQL_DB = os.environ.get('DB_NAME', 'pharmacy_management_system')
    MYSQL_CURSORCLASS = 'DictCursor'

    HOST = os.environ.get('APP_HOST', '127.0.0.1')
    ALLOWED_NETWORKS = os.environ.get('ALLOWED_NETWORKS', '')            # v79: e.g. 192.168.0.0/16,100.64.0.0/10 (empty = no limit)
    PORT = int(os.environ.get('APP_PORT', '5000'))
    DEBUG = _flag('FLASK_DEBUG', '0')

    # ---- sales ----
    TAX_RATE = float(os.environ.get('TAX_RATE', '0'))                       # % added to every sale (0 = no tax)
    CASHIER_MAX_DISCOUNT_PCT = float(os.environ.get('CASHIER_MAX_DISCOUNT', '10'))

    # ---- AI assistant (optional) ----
    # v99.00 (Stage 1, owner decision) - unchanged in v100: the AI assistant uses Google Gemini ONLY.
    # OpenAI and Claude support was removed. The key can also be saved on the
    # Settings page (app_settings), which wins over .env. Keys are never printed.
    AI_ENABLED = _flag('AI_ENABLED', '1')
    AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '15'))       # seconds, every AI call
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')
    GEMINI_FALLBACK_MODELS = [m.strip() for m in os.environ.get(
        'GEMINI_FALLBACK_MODELS', 'gemini-2.5-flash-lite,gemini-2.5-flash').split(',') if m.strip()]

    # ---- security ----
    SESSION_MINUTES = int(os.environ.get('SESSION_MINUTES', '30'))     # auto logout after this idle time
    LOGIN_MAX_FAILS = int(os.environ.get('LOGIN_MAX_FAILS', '5'))      # wrong passwords before lock
    # v87.23: WhatsApp Cloud API for the phone password-reset code (Meta Business account + approved template).
    WHATSAPP_TOKEN = os.environ.get('WHATSAPP_TOKEN', '').strip()
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '').strip()
    WHATSAPP_TEMPLATE = os.environ.get('WHATSAPP_TEMPLATE', '').strip()          # approved Authentication template, body {{1}} = code
    WHATSAPP_LANG = os.environ.get('WHATSAPP_LANG', 'en').strip() or 'en'
    WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v21.0').strip() or 'v21.0'
    OTP_MINUTES = int(os.environ.get('OTP_MINUTES', '10'))
    OTP_MAX_REQUESTS = int(os.environ.get('OTP_MAX_REQUESTS', '3'))             # codes per user per 15 minutes
    LOGIN_LOCK_MINUTES = int(os.environ.get('LOGIN_LOCK_MINUTES', '5'))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _flag('HTTPS_ONLY', '0')                   # set HTTPS_ONLY=1 when you use https
