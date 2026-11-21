"""Create an API token for the mobile app or another branch (Sprint 3).

Run:  python scripts/create_api_token.py "Mobile phone" Admin
The token is printed ONCE. Copy it to the device now; it cannot be shown again.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

import MySQLdb  # noqa: E402
from config import Config  # noqa: E402
from pharmacy.api_auth import TABLE_SQL, TOKEN_ROLES, create_token  # noqa: E402

if len(sys.argv) not in (3, 4) or sys.argv[2] not in TOKEN_ROLES:
    raise SystemExit('Usage: python scripts/create_api_token.py "Label" Admin|Pharmacist [username]\n'
                     'The username links the token to a user (needed for POS checkout).')
label, role = sys.argv[1].strip() or 'API client', sys.argv[2]
login_name = sys.argv[3].strip() if len(sys.argv) == 4 else None

db = MySQLdb.connect(host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
                     passwd=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB, charset='utf8mb4')
cur = db.cursor()
cur.execute(TABLE_SQL)
user_id = None
if login_name:
    cur.execute("SELECT user_id FROM users WHERE username = %s AND is_active = 1", (login_name,))
    found = cur.fetchone()
    if not found:
        raise SystemExit(f'No active user named {login_name}')
    user_id = found[0]
raw = create_token(cur, label, role, user_id)
db.commit()
print('Token created for', label, f'({role})')
print('Copy it now (it is shown only once):')
print(raw)
