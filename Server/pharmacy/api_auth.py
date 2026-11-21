"""API tokens (Sprint 3). A token is shown ONCE when created; only its SHA-256 hash is stored."""
import hashlib
import secrets

TOKEN_ROLES = ('Admin', 'Pharmacist')
TABLE_SQL = """CREATE TABLE IF NOT EXISTS api_tokens (
                   token_id INT AUTO_INCREMENT PRIMARY KEY,
                   label VARCHAR(80) NOT NULL,
                   token_hash CHAR(64) NOT NULL UNIQUE,
                   role VARCHAR(20) NOT NULL,
                   user_id INT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   last_used DATETIME NULL,
                   revoked TINYINT(1) NOT NULL DEFAULT 0)"""


def hash_token(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def new_token():
    """A random token that is hard to guess (about 43 characters)."""
    return 'mgk_' + secrets.token_urlsafe(32)


def create_token(cur, label, role, user_id=None):
    """Store a new token and return the raw value (the only time it is visible).
    user_id links the token to a user: needed for POS checkout (a sale must have a seller)."""
    if role not in TOKEN_ROLES:
        raise ValueError('role must be Admin or Pharmacist')
    raw = new_token()
    cur.execute("INSERT INTO api_tokens (label, token_hash, role, user_id) VALUES (%s, %s, %s, %s)",
                (label[:80], hash_token(raw), role, user_id))
    return raw


def find_token(cur, raw):
    """The active token row for this raw value, or None. Updates last_used."""
    if not raw or not raw.startswith('mgk_') or len(raw) > 200:
        return None
    cur.execute("SELECT token_id, label, role, user_id FROM api_tokens WHERE token_hash = %s AND revoked = 0",
                (hash_token(raw),))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE api_tokens SET last_used = NOW() WHERE token_id = %s", (row['token_id'],))
    return row
