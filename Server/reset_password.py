"""v87.43: set a NEW password for an existing user (for example when the Admin forgot the password).
Run on the shop PC, in the Server folder, with MySQL running:
    python reset_password.py
"""
import getpass
import bcrypt
import MySQLdb
from config import Config

username = input('Username to reset: ').strip()
if not username:
    raise SystemExit('Username is empty.')
password = getpass.getpass('New password (min 8 characters): ')
if len(password) < 8:
    raise SystemExit('Password is too short (min 8 characters).')
if password != getpass.getpass('Repeat new password: '):
    raise SystemExit('Passwords do not match.')

db = MySQLdb.connect(host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
                     passwd=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB, charset='utf8mb4')
cur = db.cursor()
cur.execute('SELECT user_id FROM users WHERE username=%s', (username,))
row = cur.fetchone()
if not row:
    raise SystemExit('No user with this username.')
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
cur.execute('UPDATE users SET password_hash=%s WHERE user_id=%s', (hashed, row[0]))
db.commit()
print('Password changed. Login with the new password.')
