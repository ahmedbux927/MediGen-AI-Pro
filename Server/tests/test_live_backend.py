"""
LIVE backend test on a real MySQL 8 scratch database (backend track, B4). Never your real data.
Run:  python tests/run_all.py --live      (also runs test_live_mysql.py)
Covers: migrations (run once), product columns and unique barcode, product import dry run and commit,
Phase 2-4 SQL (held bills, phone search, stock count, controlled register trigger, temperature),
(all-or-nothing, stock of existing items untouched), and the double-submit guard on a real sale.
It drops and rebuilds the database  medigen_live_test  on every run.
NOTE: written in a sandbox with no MySQL server. The first real run may show small SQL fixes.
"""
import os, sys, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
TEST_DB = 'medigen_live_test'

if os.environ.get('MEDIGEN_LIVE_TEST') != '1':
    print('SKIP: live backend test is off. Run:  python tests/run_all.py --live')
    sys.exit(0)

sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ['DB_NAME'] = TEST_DB                     # must be set before config is imported (see test_live_mysql.py)
if os.environ.get('TEST_DB_HOST'):
    os.environ['DB_HOST'] = os.environ['TEST_DB_HOST']
if os.environ.get('TEST_DB_USER'):
    os.environ['DB_USER'] = os.environ['TEST_DB_USER']
if 'TEST_DB_PASSWORD' in os.environ:
    os.environ['DB_PASSWORD'] = os.environ['TEST_DB_PASSWORD']

from config import Config as _Cfg
import MySQLdb
import MySQLdb.cursors

assert _Cfg.MYSQL_DB == TEST_DB, 'live backend test must use %s' % TEST_DB
PASS = FAIL = 0

def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS ' + msg)
    else:
        FAIL += 1; print('FAIL ' + msg)

def connect(db=None):
    kw = dict(host=_Cfg.MYSQL_HOST, user=_Cfg.MYSQL_USER, passwd=_Cfg.MYSQL_PASSWORD, charset='utf8mb4',
              cursorclass=MySQLdb.cursors.DictCursor)
    if db:
        kw['db'] = db
    return MySQLdb.connect(**kw)

def split_sql(text):
    stmts, buf, delim = [], [], ';'
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith('DELIMITER '):
            delim = s.split(None, 1)[1]; continue
        if not s or s.startswith('--'):
            continue
        buf.append(line)
        if s.endswith(delim):
            stmt = '\n'.join(buf).rstrip()[:-len(delim)].rstrip()
            if stmt.strip():
                stmts.append(stmt)
            buf = []
    return stmts

def fresh_database():
    conn = connect(); cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    cur.execute(f"CREATE DATABASE {TEST_DB} CHARACTER SET utf8mb4")
    cur.execute(f"USE {TEST_DB}")
    for stmt in split_sql(open(os.path.join(ROOT, 'database', 'schema.sql'), encoding='utf-8').read()):
        if stmt.upper().startswith(('CREATE DATABASE', 'USE ')):
            continue
        cur.execute(stmt)
    # roles are seeded by sample_data.sql in the real install; users need them (foreign key)
    cur.execute("INSERT IGNORE INTO roles (role_id, role_name) VALUES (1,'Admin'),(2,'Pharmacist'),(3,'Cashier')")
    conn.commit(); conn.close()

def csrf(client, path):
    html = client.get(path).get_data(as_text=True)
    m = re.search(r'name="csrf-token" content="([0-9a-f]+)"', html)
    if not m:
        m = re.search(r'name="csrf_token" value="([0-9a-f]+)"', html)
    return m.group(1) if m else ''

def main():
    import bcrypt
    try:
        fresh_database()
    except MySQLdb.Error as e:
        print('FAIL cannot connect to MySQL:', e); return 1
    check(True, 'scratch database built from schema.sql')

    import app as A
    from pharmacy.services.migrations import run_migrations
    from pharmacy.services.product_import import read_file, build_plan, apply_plan, name_key
    A.app.config['TESTING'] = True
    A.app.config['SESSION_COOKIE_SECURE'] = False
    A.app.template_folder = os.path.join(ROOT, 'templates')

    with A.app.app_context():
        A.ensure_schema()
        db = A.mysql.connection
        cur = db.cursor()
        cur.execute("SELECT version FROM schema_version")
        versions = [r['version'] for r in cur.fetchall()]
        check(2 in versions, 'migration 002 (sale_guard) recorded in schema_version')
        check(run_migrations(cur) == [], 'migrations run once: a second run applies nothing')
        cur.execute("SELECT COUNT(*) AS n FROM information_schema.columns WHERE table_schema=DATABASE() "
                    "AND table_name='medicines' AND column_name='rx_required'")
        check(cur.fetchone()['n'] == 1, 'product columns added to medicines (rx_required present)')
        cur.execute("SELECT COUNT(*) AS n FROM information_schema.statistics WHERE table_schema=DATABASE() "
                    "AND table_name='medicines' AND index_name='uq_medicines_barcode'")
        check(cur.fetchone()['n'] > 0, 'unique index on medicines.barcode created')
        cur.close()

        # ---- product import: dry run, then commit (all-or-nothing) ----
        rows, _ = read_file(open(os.path.join(ROOT, 'database', 'samples', 'pharmacy_products_230_demo.csv'), 'rb').read(),
                            'pharmacy_products_230_demo.csv')
        cur = db.cursor()
        cur.execute("SELECT medicine_id, name, barcode, stock_quantity FROM medicines")
        before = {r['medicine_id']: r for r in cur.fetchall()}
        existing = {'barcodes': {r['barcode']: r for r in before.values() if r['barcode']},
                    'names': {name_key(r['name']): r for r in before.values()}}
        plan, summary = build_plan(rows, existing, datetime.date.today())
        check(summary['counts']['error'] == 0, 'dry run: no error rows in the 230-product file')
        check(summary['counts']['create'] + summary['counts']['skip'] == 230, 'dry run: every row is create or skip')
        stock_before = {mid: r['stock_quantity'] for mid, r in before.items()}
        expected_create = summary['counts']['create']
        with A.app.test_request_context():
            done = apply_plan(cur, plan, 'live-test.csv', audit_fn=A.audit)
        db.commit()
        cur.execute("SELECT COUNT(*) AS n FROM medicines")
        check(cur.fetchone()['n'] == len(before) + expected_create, 'commit: one medicine row per created product')
        cur.execute("SELECT COUNT(*) AS n FROM batches WHERE medicine_id IN "
                    "(SELECT medicine_id FROM medicines WHERE import_source='live-test.csv') AND quantity > 0")
        check(cur.fetchone()['n'] == done['batches'], 'commit: one batch per created product with stock')
        cur.execute("SELECT medicine_id, stock_quantity FROM medicines")
        after = {r['medicine_id']: r['stock_quantity'] for r in cur.fetchall()}
        changed = [mid for mid, qty in stock_before.items() if after.get(mid) != qty]
        check(not changed, 'existing items keep their stock after import')
        # a second import of the same file must create nothing (every row is now a skip)
        cur.execute("SELECT medicine_id, name, barcode, stock_quantity FROM medicines")
        rows_now = cur.fetchall()
        existing2 = {'barcodes': {r['barcode']: r for r in rows_now if r['barcode']},
                     'names': {name_key(r['name']): r for r in rows_now}}
        _, summary2 = build_plan(rows, existing2, datetime.date.today())
        check(summary2['counts']['create'] == 0, 'second import of the same file creates nothing (no duplicates)')
        cur.close()

        # ---- double submit on a real sale (route + guard + database) ----
        pw = 'Live-Backend-2026'
        cur = db.cursor()
        cur.execute("INSERT INTO users (full_name, username, password_hash, role_id) VALUES ('Live Backend','livebackend',%s,1)",
                    (bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode(),))
        db.commit(); cur.close()
        c = A.app.test_client()
        r = c.post('/login', data={'username': 'livebackend', 'password': pw, 'csrf_token': csrf(c, '/login')})
        check(r.status_code == 302, 'login as a test user')
        cur = db.cursor()
        cur.execute("SELECT medicine_id FROM medicines WHERE import_source='live-test.csv' AND stock_quantity > 0 LIMIT 1")
        mid = cur.fetchone()['medicine_id']
        cur.close()
        # v90.00 fix: a cash sale needs an open drawer since v87.03 (by design) -
        # open it first, like the shop does every morning
        c.post('/cash/open', data={'csrf_token': csrf(c, '/sales/new'), 'opening': '1000'})
        form = {'csrf_token': csrf(c, '/sales/new'), 'payment_method': 'Cash',
                'medicine_id[]': [str(mid)], 'quantity[]': ['1']}
        r1 = c.post('/sales/new', data=form)
        r2 = c.post('/sales/new', data=form)
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM sales s JOIN sale_items si ON si.sale_id = s.sale_id "
                    "WHERE si.medicine_id = %s AND s.user_id = (SELECT user_id FROM users WHERE username='livebackend')",
                    (mid,))
        n = cur.fetchone()['n']
        cur.close()
        check(r1.status_code == 302 and 'invoice' in r1.headers.get('Location', ''), 'first submit saves the sale')
        check(r2.status_code == 302 and '/sales' in r2.headers.get('Location', ''), 'second submit is refused')
        check(n == 1, 'double submit: exactly one sale in the database')

        # ---- Phase 2-4 SQL on real MySQL (held bills, phone search, stock count, register, temperature) ----
        from pharmacy.services import held_bills as HB, stock_count as SC, phone_search as PS
        from pharmacy.services import controlled_register as CR, temperature as TP
        from pharmacy.services.sales import BillError, check_scheduled
        cur = db.cursor()
        cur.execute("SELECT user_id FROM users WHERE username='livebackend'")
        uid = cur.fetchone()['user_id']
        cur.execute("SELECT medicine_id FROM medicines WHERE import_source='live-test.csv' AND stock_quantity > 1 "
                    "ORDER BY medicine_id LIMIT 2")
        mids = [r['medicine_id'] for r in cur.fetchall()]
        cur.close()
        mid_a, mid_b = mids[0], mids[1]

        cur = db.cursor()
        hid = HB.hold_bill(cur, uid, 1, None, {mid_a: 2}, 'live hold')
        db.commit()
        holds = [h['hold_id'] for h in HB.open_holds(cur, 1)]
        check(hid in holds, 'hold bill saved on a real database and listed as open')
        payload = HB.resume_hold(cur, hid)
        db.commit()
        check(payload['lines'] == [{'medicine_id': mid_a, 'quantity': 2}], 'resume returns the held lines')
        try:
            HB.resume_hold(cur, hid); check(False, 'a held bill cannot be resumed twice')
        except HB.HoldError:
            check(True, 'a held bill cannot be resumed twice')
        cur.close()

        cur = db.cursor()
        cur.execute("INSERT INTO customers (name, contact_number) VALUES ('Live Phone Test', '0300-7654321')")
        db.commit()
        found = PS.search_customers(cur, '7654321')
        check(any(r['name'] == 'Live Phone Test' for r in found), 'phone search finds the customer with a formatted number')
        check(PS.search_customers(cur, '12') == [], 'phone search: too short returns nothing')
        cur.close()

        cur = db.cursor()
        cnt = SC.start_count(cur, uid, 'live count')
        cur.execute("SELECT stock_quantity FROM medicines WHERE medicine_id=%s", (mid_b,))
        stock_b = cur.fetchone()['stock_quantity']
        cur.execute("SELECT medicine_id, stock_quantity FROM medicines")
        for row in cur.fetchall():                      # a count must cover every medicine before submit
            qty = row['stock_quantity'] + (5 if row['medicine_id'] == mid_b else 0)
            SC.record_count(cur, cnt, row['medicine_id'], qty, uid)
        SC.submit_count(cur, cnt)
        db.commit()
        SC.approve_count(cur, cnt, uid, 'Admin', A.audit)
        db.commit()
        cur.execute("SELECT stock_quantity FROM medicines WHERE medicine_id=%s", (mid_b,))
        check(cur.fetchone()['stock_quantity'] == stock_b + 5, 'stock count approval sets stock to the counted quantity')
        cur.execute("SELECT COUNT(*) AS n FROM stock_adjustments WHERE medicine_id=%s AND reason='Stock count'", (mid_b,))
        check(cur.fetchone()['n'] >= 1, 'stock count approval writes a stock adjustment row')
        cur.close()

        cur = db.cursor()
        cur.execute("UPDATE medicines SET schedule='Narcotic' WHERE medicine_id=%s", (mid_a,))
        db.commit()
        try:
            check_scheduled(cur, [(mid_a, 1.0, [(None, 1)])], None)
            check(False, 'scheduled medicine without prescription is refused (real database)')
        except BillError:
            check(True, 'scheduled medicine without prescription is refused (real database)')
        CR.write_entries(cur, 0, uid, None, None, [{'medicine_id': mid_a, 'schedule': 'Narcotic',
                                                     'batch_id': None, 'quantity': 1}])
        db.commit()
        try:
            cur.execute("UPDATE controlled_register SET quantity=2 WHERE sale_id=0")
            check(False, 'controlled register rejects UPDATE (append-only trigger)')
        except MySQLdb.Error:
            check(True, 'controlled register rejects UPDATE (append-only trigger)')
        cur.close()

        cur = db.cursor()
        r = TP.record_reading(cur, 'Live Fridge', '9.5', uid, 'out of range test')
        db.commit()
        check(r['in_range'] is False, 'temperature 9.5 is saved as out of range')
        cur.close()

        # ---- audit log is append-only at the database level ----
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM information_schema.triggers WHERE trigger_schema=DATABASE() "
                    "AND trigger_name IN ('trg_audit_no_update','trg_audit_no_delete')")
        check(cur.fetchone()['n'] == 2, 'audit log triggers exist (update and delete blocked)')
        cur.close()

    print(f'{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0

if __name__ == '__main__':
    sys.exit(main())
