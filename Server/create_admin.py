"""
Creates the first Admin user (needed only on a NEW empty database).
Run:  python create_admin.py
"""
import getpass
import bcrypt
import MySQLdb
from config import Config

username = input('Admin username [admin]: ').strip() or 'admin'
full_name = input('Full name [Administrator]: ').strip() or 'Administrator'
password = getpass.getpass('Password (min 8 characters): ')
if len(password) < 8:
    raise SystemExit('Password is too short.')
if password != getpass.getpass('Repeat password: '):
    raise SystemExit('Passwords do not match.')

db = MySQLdb.connect(host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
                     passwd=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB, charset='utf8mb4')
cur = db.cursor()
cur.execute('SELECT user_id FROM users WHERE username=%s', (username,))
if cur.fetchone():
    raise SystemExit('This username already exists.')
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
cur.execute('INSERT INTO users (full_name, username, password_hash, role_id) VALUES (%s,%s,%s,1)',
            (full_name, username, hashed))
db.commit()
print('Admin user created. You can login now.')
