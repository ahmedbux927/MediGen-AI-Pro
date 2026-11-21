"""
LIVE test on a real MySQL 8 database (a scratch copy, never your real data).
Run:  python tests/run_all.py --live
It uses the same DB user/password as your .env (unless TEST_DB_* is set).
It drops and rebuilds the database  medigen_live_test  on every run.
"""
import os, sys, io, glob, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
TEST_DB = 'medigen_live_test'

if os.environ.get('MEDIGEN_LIVE_TEST') != '1':
    print('SKIP: live test is off. Run:  python tests/run_all.py --live')
    sys.exit(0)

sys.path.insert(0, ROOT)
os.chdir(ROOT)

# config.py reads DB_NAME / DB_HOST / DB_USER / DB_PASSWORD ONCE, when it is first imported.
# So the test database name must be set BEFORE 'import config' (or the app would use the real
# pharmacy database while the test writes to medigen_live_test). Real environment values win over .env.
os.environ['DB_NAME'] = TEST_DB
if os.environ.get('TEST_DB_HOST'):
    os.environ['DB_HOST'] = os.environ['TEST_DB_HOST']
if os.environ.get('TEST_DB_USER'):
    os.environ['DB_USER'] = os.environ['TEST_DB_USER']
if 'TEST_DB_PASSWORD' in os.environ:
    os.environ['DB_PASSWORD'] = os.environ['TEST_DB_PASSWORD']

from config import Config as _Cfg          # now reads the test database settings above
import MySQLdb

DB_HOST = _Cfg.MYSQL_HOST
DB_USER = _Cfg.MYSQL_USER
DB_PASS = _Cfg.MYSQL_PASSWORD
assert _Cfg.MYSQL_DB == TEST_DB, 'live test must use %s, not %s' % (TEST_DB, _Cfg.MYSQL_DB)

ok_count = [0]
fail_count = [0]


def _csrf(client, path='/dashboard'):
    """Read the CSRF token from a page, the same way a real browser form gets it."""
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf-token" content="([0-9a-f]+)"', html)
    assert m, 'no csrf token on ' + path
    return m.group(1)

def check(cond, msg):
    if cond:
        ok_count[0] += 1
        print('PASS ' + msg)
    else:
        fail_count[0] += 1
        print('FAIL ' + msg)

def connect(db=None):
    kwargs = dict(host=DB_HOST, user=DB_USER, passwd=DB_PASS, charset='utf8mb4')
    if db:
        kwargs['db'] = db
    return MySQLdb.connect(**kwargs)

def split_sql(text):
    """Split a .sql file into statements. Understands DELIMITER blocks (triggers)."""
    stmts, buf, delim = [], [], ';'
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith('DELIMITER '):
            delim = s.split(None, 1)[1]
            continue
        if not s or s.startswith('--'):
            continue
        buf.append(line)
        if s.endswith(delim):
            stmt = '\n'.join(buf).rstrip()
            stmt = stmt[:-len(delim)].rstrip()
            if stmt.strip():
                stmts.append(stmt)
            buf = []
    return stmts

def fresh_database():
    conn = connect()
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    cur.execute(f"CREATE DATABASE {TEST_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    cur.execute(f"USE {TEST_DB}")
    for name in ('schema.sql', 'sample_data.sql'):
        text = open(os.path.join(ROOT, 'database', name), encoding='utf-8').read()
        for stmt in split_sql(text):
            up = stmt.upper()
            if up.startswith('CREATE DATABASE') or up.startswith('USE '):
                continue
            cur.execute(stmt)
    conn.commit()
    conn.close()

def main():
    import bcrypt
    try:
        fresh_database()
    except MySQLdb.Error as e:
        print(f"FAIL cannot connect to MySQL as '{DB_USER}': {e}")
        print("     Check DB_USER / DB_PASSWORD in .env (or set TEST_DB_PASSWORD) and that MySQL is running.")
        sys.exit(1)
    check(True, 'scratch database built from schema.sql + sample_data.sql')

    import app as A
    A.app.config['TESTING'] = True
    # The test talks plain http to the app. If .env has HTTPS_ONLY=1 the login cookie would be
    # marked secure and never sent back, so every page would redirect to login. Turn that off here only.
    A.app.config['SESSION_COOKIE_SECURE'] = False
    A.app.template_folder = os.path.join(ROOT, 'templates')

    pw = 'Live-Admin-2026'
    db = connect(TEST_DB)
    cur = db.cursor()
    cur.execute("INSERT INTO users (full_name, username, password_hash, role_id) VALUES ('Live Admin','liveadmin',%s,1)",
                (bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),))
    db.commit()

    c = A.app.test_client()
    r = c.post('/login', data={'username': 'liveadmin', 'password': pw, 'csrf_token': _csrf(c, '/login')})
    check(r.status_code == 302 and r.headers.get('Location', '').endswith('/dashboard'),
          'real login with a bcrypt password works (goes to dashboard)')
    check(c.get('/dashboard').status_code == 200, 'dashboard loads from the real database')
    for url in ['/medicines', '/batches', '/sales', '/sales/new', '/purchase', '/purchase/new', '/prescriptions',
                '/prescriptions/add', '/reports', '/settings', '/customers', '/suppliers', '/chatbot']:
        r = c.get(url)
        check(r.status_code == 200, f'page opens: {url} (got {r.status_code})')

    cur.execute("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = DATABASE() AND TRIGGER_NAME = 'trg_sale_stock'")
    check(cur.fetchone()[0] == 1, 'the sale stock trigger exists in the live database')
    cur.execute("SELECT stock_quantity FROM medicines WHERE medicine_id=1")
    before = cur.fetchone()[0]
    # v90.00 fix: since v87.03 a cash sale needs an open drawer (by design). Open it
    # first, the way the shop does every morning - this test used to fail on a
    # clean database because no drawer session existed.
    r_open = c.post('/cash/open', data={'csrf_token': _csrf(c), 'opening': '1000'})
    check(r_open.status_code == 302, 'cash drawer opens for the day')
    r = c.post('/sales/new', data={'csrf_token': _csrf(c), 'payment_method': 'Cash', 'medicine_id[]': ['1'], 'quantity[]': ['3']})
    db.commit()   # end the old read snapshot, so the new stock and the audit row are visible
    cur.execute("SELECT stock_quantity FROM medicines WHERE medicine_id=1")
    after = cur.fetchone()[0]
    with c.session_transaction() as sess:
        flashed = ' | '.join(m for _, m in sess.get('_flashes', []))
    check(r.status_code == 302 and after == before - 3,
          f'sale of 3 units lowers stock {before} -> {after} (page said: {flashed or "no message"})')
    cur.execute("SELECT COUNT(*) FROM audit_log WHERE action='sale.create'")
    check(cur.fetchone()[0] >= 1, 'the sale is in the audit log')
    cur.execute("SELECT COUNT(*) FROM batches WHERE medicine_id=1 AND quantity < 0")
    check(cur.fetchone()[0] == 0, 'no batch went negative')

    try:
        cur.execute("UPDATE audit_log SET details='changed' WHERE audit_id=1")
        db.commit()
        check(False, 'audit row could be UPDATED (must be blocked)')
    except MySQLdb.Error as e:
        check(e.args[0] == 1644 or 'append-only' in str(e).lower(), 'audit row cannot be UPDATEd in the database')
        db.rollback()
    try:
        cur.execute("DELETE FROM audit_log WHERE audit_id=1")
        db.commit()
        check(False, 'audit row could be DELETED (must be blocked)')
    except MySQLdb.Error as e:
        check(e.args[0] == 1644 or 'append-only' in str(e).lower(), 'audit row cannot be DELETEd in the database')
        db.rollback()

    r = c.post('/prescriptions/add', data={'csrf_token': _csrf(c), 'customer_id': '1', 'doctor_name': 'Dr. Live',
                                           'medicine_id[]': ['1'], 'dosage[]': ['1 tab'], 'duration[]': ['3']})
    check(r.status_code == 302, 'prescription saved')
    cur.execute("SELECT MAX(prescription_id) FROM prescriptions")
    pid = cur.fetchone()[0]
    c.post('/sales/new', data={'csrf_token': _csrf(c), 'payment_method': 'Cash', 'medicine_id[]': ['1'],
                               'quantity[]': ['1'], 'prescription_id': str(pid)})
    db.commit()   # v90.00 fix: end the old read snapshot (same pattern as the first sale check above)
    cur.execute("SELECT COUNT(*) FROM sales WHERE prescription_id=%s", (pid,))
    check(cur.fetchone()[0] == 1, 'prescription dispensed into a sale (linked)')
    c.post(f'/prescriptions/{pid}/delete', data={'csrf_token': _csrf(c)})
    cur.execute("SELECT COUNT(*) FROM prescriptions WHERE prescription_id=%s", (pid,))
    check(cur.fetchone()[0] == 1, 'dispensed prescription is NOT deleted')

    cur.execute("SELECT MAX(sale_id) FROM sales")
    sid = cur.fetchone()[0]
    db.close()
    c2 = A.app.test_client()
    c2.post('/login', data={'username': 'liveadmin', 'password': pw, 'csrf_token': _csrf(c2, '/login')})
    check(c2.get(f'/invoice/{sid}').status_code == 200, 'invoice page renders')
    check(c2.get(f'/invoice/{sid}/thermal').status_code == 200, '80mm receipt renders')
    check(c2.get('/reports/export/sales').status_code == 200, 'sales CSV export works')
    print(f"\nLIVE: {ok_count[0]} passed, {fail_count[0]} failed")
    sys.exit(1 if fail_count[0] else 0)

if __name__ == '__main__':
    main()
