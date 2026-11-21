"""Shared setup: Flask app, database handle, CSRF, login lock, schema checks, decorators."""
import os
import re
import time
import hmac
import hashlib
import secrets
import math
import csv
import io
import json
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_from_directory, g
from flask_mysqldb import MySQL
import bcrypt
from functools import wraps
from datetime import datetime, timedelta, date
from chatbot_engine import get_answer, DEFAULT_CHIPS, NOT_UNDERSTOOD   # MediGen AI chatbot
from config import Config
from pharmacy.services.product_import import PRODUCT_COLUMNS   # Phase 1 product fields
from pharmacy.services.migrations import run_migrations   # B2: numbered schema migrations
from pharmacy.services.controlled_register import ensure_register_triggers   # Phase 4: append-only register


app = Flask(__name__,
            template_folder=os.path.join(Config.BASE_DIR, 'templates'),
            static_folder=os.path.join(Config.BASE_DIR, 'static'),
            static_url_path='/static')
app.config.from_object(Config)      # all settings come from config.py / .env
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024      # uploads (backup files) up to 200 MB
# v88.00: B5 - About page version comes from Config.APP_VERSION (one source), not a hard-coded copy
APP_VERSION = Config.APP_VERSION
APP_RELEASE_DATE = '20 Nov 2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=Config.SESSION_MINUTES)

# Errors are also written to a log file (logs/medigen.log next to the app), so a shop can send it after a failure.
# The exe runs without a console window, so the console is not enough. Rotates at 2 MB, keeps 5 old files.
import logging as _logging
from logging.handlers import RotatingFileHandler as _RotatingFileHandler
try:
    _log_dir = os.path.join(Config.BASE_DIR, 'logs')
    os.makedirs(_log_dir, exist_ok=True)
    _file_handler = _RotatingFileHandler(os.path.join(_log_dir, 'medigen.log'), maxBytes=5 * 1024 * 1024,
                                         backupCount=5, encoding='utf-8')
    _file_handler.setLevel(_logging.WARNING)
    _file_handler.setFormatter(_logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    app.logger.addHandler(_file_handler)
    app.logger.setLevel(_logging.INFO)
except OSError as _log_exc:
    # Read-only folder: the console log still works. Never silent (Stage 2 rule).
    print(f'WARNING: file logging unavailable ({_log_exc}); console log only.', file=sys.stderr)

# =====================================================================
#  SECURITY LAYER  (CSRF token, login lock, password rules, headers)
# =====================================================================
def get_csrf_token():
    """One secret token per login session. Every POST must send it back."""
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(24)
    return session['_csrf']

app.add_template_global(get_csrf_token, 'csrf_token')

@app.context_processor
def _inject_app_version():
    # v101: every template can show the real version from config; no hard-coded copies.
    return {'app_version': Config.APP_VERSION}

@app.before_request
def _network_gate():
    """v79: refuse connections from addresses outside ALLOWED_NETWORKS (only when that list is set)."""
    from pharmacy.services import net_access as NA
    nets, _bad = NA.parse_networks(Config.ALLOWED_NETWORKS)
    if NA.is_allowed(request.remote_addr, nets):
        return None
    app.logger.warning('blocked connection from %s (not in ALLOWED_NETWORKS)', request.remote_addr)
    return ('This app only accepts connections from the shop network or the owner VPN.', 403,
            {'Content-Type': 'text/plain; charset=utf-8'})

@app.before_request
def csrf_protect():
    if request.method in ('GET', 'HEAD', 'OPTIONS') or request.endpoint == 'static':
        return None
    # v88.00: CSRF exemptions - the COMPLETE, deliberate list (tested in tests/test_v88_security.py):
    #   1. Any /api/ call that sends an Authorization Bearer token: the token is not a cookie,
    #      so a cross-site form cannot send it. CSRF cannot apply.
    #   2. POST /api/auth/login only: it creates a token; the caller must know the password,
    #      and no browser cookie session exists yet to forge.
    # No other route is exempt. (The v87 WhatsApp OTP endpoints were removed in v88.00.)
    if request.path.startswith('/api/') and (request.headers.get('Authorization', '').lower().startswith('bearer ')
                                             or request.path == '/api/auth/login'):
        return None
    sent = request.form.get('csrf_token') or request.headers.get('X-CSRFToken') or ''
    expected = session.get('_csrf', '')
    if not expected or not hmac.compare_digest(sent, expected):
        if request.path.startswith('/chatbot/api') or request.is_json:
            return jsonify({'error': 'Security check failed. Please refresh the page and try again.'}), 400
        flash('Security check failed or session expired. Please try again.', 'warning')
        return redirect(request.referrer or url_for('login'))
    return None

_FORM_RE = re.compile(r'(<form\b[^>]*\bmethod\s*=\s*["\']?post["\']?[^>]*>)', re.I)

@app.after_request
def secure_response(resp):
    """Add the CSRF field to every POST form automatically + safe browser headers."""
    try:
        if resp.mimetype == 'text/html' and not resp.direct_passthrough and resp.status_code != 304:
            body = resp.get_data(as_text=True)
            token = get_csrf_token()
            hidden = '<input type="hidden" name="csrf_token" value="%s">' % token
            body = _FORM_RE.sub(lambda m: m.group(1) + hidden, body)
            body = body.replace('<head>', '<head><meta name="csrf-token" content="%s">' % token, 1)
            resp.set_data(body)
    except Exception:
        app.logger.exception('security injection failed')
    resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    # v100.00: Content-Security-Policy - the app may only load its own files plus
    # its two known CDNs (Bootstrap assets + Google Fonts). Inline script/style is
    # allowed because the server-rendered pages use it; no other origin can inject.
    resp.headers.setdefault('Content-Security-Policy',
        "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'self'; "
        "base-uri 'self'; form-action 'self'")
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('Referrer-Policy', 'same-origin')
    resp.headers.setdefault('Permissions-Policy', 'camera=(self), microphone=(self), geolocation=()')  # v88.00: E7
    if request.endpoint != 'static':
        resp.headers.setdefault('Cache-Control', 'no-store')
    return resp

# ---- login lock: too many wrong passwords = wait a few minutes ----
# Stored in the login_attempts table, so a restart or a second worker does not reset it.
# The key is a hash of IP + username, so no raw username or IP is kept in the table.
DUMMY_HASH = bcrypt.hashpw(b'medigen-dummy-password', bcrypt.gensalt())   # checked when the user does not exist (same timing)

def _lock_key(ip, username):
    return hashlib.sha256(f"{ip}|{username.lower()}".encode('utf-8')).hexdigest()

def _lock_left(key):
    """Seconds left on the lock, 0 when not locked."""
    cur = mysql.connection.cursor()
    cur.execute("SELECT locked_until FROM login_attempts WHERE lock_key=%s", (key,))
    row = cur.fetchone()
    cur.close()
    until = int((row or {}).get('locked_until') or 0)
    left = until - int(time.time())
    return left if left > 0 else 0

def _register_fail(key):
    """Count one wrong password. Returns attempts left (0 means locked now)."""
    now = int(time.time())
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT fail_count, locked_until FROM login_attempts WHERE lock_key=%s FOR UPDATE", (key,))
        row = cur.fetchone() or {}
        count = int(row.get('fail_count') or 0)
        until = int(row.get('locked_until') or 0)
        if until and until <= now:                       # old lock finished, start again
            count, until = 0, 0
        count += 1
        if count >= Config.LOGIN_MAX_FAILS:
            until = now + Config.LOGIN_LOCK_MINUTES * 60
        cur.execute("""INSERT INTO login_attempts (lock_key, fail_count, locked_until) VALUES (%s,%s,%s)
                       ON DUPLICATE KEY UPDATE fail_count=VALUES(fail_count), locked_until=VALUES(locked_until)""",
                    (key, count, until))
        mysql.connection.commit()
    finally:
        cur.close()
    return max(0, Config.LOGIN_MAX_FAILS - count)

def _clear_fails(key):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM login_attempts WHERE lock_key=%s", (key,))
        mysql.connection.commit()
    finally:
        cur.close()

# ---- password rules ----
WEAK_PASSWORDS = {'password', 'password1', 'admin123', 'admin1234', '12345678', 'qwerty123', 'pharmacy123', 'abc12345'}

def password_error(pw, username=''):
    """Return a message if the password is weak, else None."""
    if len(pw) < 8:
        return 'Password must be at least 8 characters'
    if not re.search(r'[A-Za-z]', pw) or not re.search(r'\d', pw):
        return 'Password must contain both letters and numbers'
    if pw.lower() in WEAK_PASSWORDS:
        return 'This password is too common. Choose a different one'
    if username and pw.lower() == username.lower():
        return 'Password must not be the same as the username'
    return None

mysql = MySQL(app)

# =====================================================================
#  DATABASE AUTO-UPDATE  (adds new columns/tables the first time, safe to repeat)
# =====================================================================
_schema_ready = False

AUDIT_TRIGGERS = [
    ('trg_audit_no_update', "CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON audit_log FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Audit log is append-only: updates are not allowed'; END"),
    ('trg_audit_no_delete', "CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON audit_log FOR EACH ROW BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Audit log is append-only: deletes are not allowed'; END"),
]

def ensure_medicine_hidden_column(cur):
    """v86.29: medicines.is_deleted = 1 hides a medicine from every list and picker. Bills and purchases keep it."""
    cur.execute("""SELECT COUNT(*) AS n FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'medicines' AND COLUMN_NAME = 'is_deleted'""")
    if not cur.fetchone()['n']:
        cur.execute("ALTER TABLE medicines ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0")
        app.logger.warning('medicines.is_deleted column added')


def ensure_hidden_views(cur):
    """v86.37: the two dashboard views skip hidden (deleted) medicines. Re-created on every start (idempotent)."""
    try:
        cur.execute("""CREATE OR REPLACE VIEW v_expiring_soon AS
                       SELECT b.batch_id, m.name, b.batch_number, b.expiry_date, b.quantity
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE m.is_deleted = 0 AND b.expiry_date BETWEEN CURDATE() AND (CURDATE() + INTERVAL 90 DAY)""")
        cur.execute("""CREATE OR REPLACE VIEW v_low_stock AS
                       SELECT medicine_id, name, stock_quantity, reorder_level
                       FROM medicines WHERE is_deleted = 0 AND stock_quantity <= reorder_level""")
    except Exception:
        app.logger.warning('dashboard views not updated for hidden medicines')


def ensure_stock_triggers():
    """v83: sales and purchases move stock through triggers. Create them if the database lacks them."""
    from pharmacy.services import stock_triggers as ST
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT TRIGGER_NAME AS name, EVENT_OBJECT_TABLE AS tbl FROM information_schema.TRIGGERS
                       WHERE TRIGGER_SCHEMA = DATABASE() AND EVENT_MANIPULATION = 'INSERT'""")
        todo = ST.missing([(r['name'], r['tbl']) for r in cur.fetchall()])
        for name, table, ddl in todo:
            cur.execute(ddl)
            app.logger.warning('stock trigger %s was missing on %s and has been created', name, table)
        if todo:
            mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        app.logger.error('stock triggers missing and could not be created: sales may not lower stock. '
                         'Give the database user TRIGGER permission, then restart.', exc_info=True)
    finally:
        cur.close()


def ensure_audit_triggers():
    """Audit rows can be added but never changed or deleted (even by a direct SQL UPDATE/DELETE).
    If the database user has no TRIGGER permission, the app still runs and logs a warning."""
    cur = mysql.connection.cursor()
    try:
        for name, ddl in AUDIT_TRIGGERS:
            cur.execute(f"DROP TRIGGER IF EXISTS {name}")
            cur.execute(ddl)
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        app.logger.warning('audit append-only triggers not created (needs TRIGGER permission)', exc_info=True)
    finally:
        cur.close()

AUDIT_COLUMNS = {
    'request_id': 'VARCHAR(16) NULL',
    'request_path': 'VARCHAR(200) NULL',
    'http_method': 'VARCHAR(8) NULL',
    'user_agent': 'VARCHAR(255) NULL',
    'status': "VARCHAR(10) NOT NULL DEFAULT 'ok'",
    'old_values': 'MEDIUMTEXT NULL',
    'new_values': 'MEDIUMTEXT NULL',
}

def ensure_schema():
    """Step 3: cost_price column + stock_adjustments table."""
    global _schema_ready
    if _schema_ready:
        return
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT COUNT(*) AS n FROM information_schema.columns
                       WHERE table_schema = DATABASE() AND table_name = 'medicines' AND column_name = 'cost_price'""")
        if cur.fetchone()['n'] == 0:
            cur.execute("ALTER TABLE medicines ADD COLUMN cost_price DECIMAL(15,2) NOT NULL DEFAULT 0 AFTER price")
            # first fill: use the last purchase price we know
            cur.execute("""UPDATE medicines m SET m.cost_price = COALESCE(
                              (SELECT pi.unit_price FROM purchase_items pi WHERE pi.medicine_id = m.medicine_id
                               ORDER BY pi.po_item_id DESC LIMIT 1),
                              (SELECT b.purchase_price FROM batches b WHERE b.medicine_id = m.medicine_id
                               ORDER BY b.batch_id DESC LIMIT 1), 0)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS stock_adjustments (
                           adjustment_id INT AUTO_INCREMENT PRIMARY KEY,
                           medicine_id INT NOT NULL,
                           user_id INT NULL,
                           change_qty INT NOT NULL,
                           old_stock INT NOT NULL,
                           new_stock INT NOT NULL,
                           reason VARCHAR(40) NOT NULL,
                           note VARCHAR(255) NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_adj_medicine (medicine_id),
                           CONSTRAINT fk_adj_medicine FOREIGN KEY (medicine_id)
                               REFERENCES medicines (medicine_id) ON DELETE CASCADE
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        # ---- Step 5: discount / tax / credit / returns ----
        def has_col(table, col):
            cur.execute("""SELECT COUNT(*) AS n FROM information_schema.columns
                           WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s""", (table, col))
            return cur.fetchone()['n'] > 0
        if not has_col('medicines', 'barcode'):          # Step 7: barcode for fast billing
            cur.execute("ALTER TABLE medicines ADD COLUMN barcode VARCHAR(64) NULL AFTER name")
        fresh = False
        for col, ddl in [('subtotal_amount', 'DECIMAL(15,2) NOT NULL DEFAULT 0'),
                         ('discount_amount', 'DECIMAL(15,2) NOT NULL DEFAULT 0'),
                         ('tax_rate', 'DECIMAL(5,2) NOT NULL DEFAULT 0'),
                         ('tax_amount', 'DECIMAL(15,2) NOT NULL DEFAULT 0'),
                         ('paid_amount', 'DECIMAL(15,2) NOT NULL DEFAULT 0'),
                         ('returned_amount', 'DECIMAL(15,2) NOT NULL DEFAULT 0'),
                         ('prescription_id', 'INT NULL'),
                         ('client_uuid', 'VARCHAR(64) NULL')]:   # v86.62: offline bill id, sent once only
            if not has_col('sales', col):
                cur.execute(f"ALTER TABLE sales ADD COLUMN {col} {ddl}")
                if col == 'paid_amount':
                    fresh = True
        cur.execute("""SELECT COUNT(*) AS n FROM information_schema.STATISTICS
                       WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'sales'
                       AND INDEX_NAME = 'uq_sales_client_uuid'""")
        if not cur.fetchone()['n']:
            try:   # v86.62: two sales with the same offline id cannot both be saved. NULL ids are allowed many times.
                cur.execute("ALTER TABLE sales ADD UNIQUE KEY uq_sales_client_uuid (client_uuid)")
            except Exception:
                app.logger.exception('sales client_uuid unique key not added (duplicate ids in old data?)')
        # v94.00: mobile wallets. sales.payment_method is an ENUM in older databases;
        # widen it in place (existing values keep working, nothing renamed or removed).
        cur.execute("""SELECT COLUMN_TYPE AS t FROM information_schema.columns
                       WHERE table_schema = DATABASE() AND table_name = 'sales' AND column_name = 'payment_method'""")
        _pm = (cur.fetchone() or {}).get('t', '') or ''
        if 'JazzCash' not in _pm:
            cur.execute("ALTER TABLE sales MODIFY payment_method ENUM('Cash','Card','Online','JazzCash','Easypaisa') DEFAULT 'Cash'")
        if fresh:     # old sales were all paid in full, without discount or tax
            cur.execute("UPDATE sales SET subtotal_amount = total_amount, paid_amount = total_amount")
        # Users: profile and access columns. Databases made from an older schema lack some of them,
        # which made every profile save fail ("Unknown column"). Add whatever is missing.
        USER_COLUMNS = [
            ('is_active', 'TINYINT(1) DEFAULT 1'),
            ('created_at', 'TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP'),
            ('access_start_time', "TIME DEFAULT '08:00:00'"),
            ('access_end_time', "TIME DEFAULT '22:00:00'"),
            ('gender', 'VARCHAR(20) NULL'),
            ('email', 'VARCHAR(100) NULL'),
            ('phone', 'VARCHAR(20) NULL'),
            ('birthday', 'DATE NULL'),
            ('language', 'VARCHAR(50) NULL'),
            ('home_address', 'VARCHAR(255) NULL'),
            ('work_address', 'VARCHAR(255) NULL'),
            ('other_address', 'VARCHAR(255) NULL'),
            ('about', 'TEXT NULL'),
            ('position', 'VARCHAR(100) NULL'),
            ('projects', 'TEXT NULL'),
            ('license_info', 'VARCHAR(255) NULL'),
            ('experience', 'TEXT NULL'),
            ('recommendations', 'TEXT NULL'),
            ('volunteer', 'TEXT NULL'),
            ('honors', 'TEXT NULL'),
            ('awards', 'TEXT NULL'),
            ('causes', 'TEXT NULL'),
            ('services', 'TEXT NULL'),
            ('profile_pic', 'VARCHAR(255) NULL'),
        ]
        for col, ddl in USER_COLUMNS:
            if not has_col('users', col):
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
                app.logger.info('Added missing users.%s column', col)

        # Sprint 1: expired / damaged stock sent back to the supplier (a record, not a sale)
        cur.execute("""CREATE TABLE IF NOT EXISTS supplier_returns (
                           return_id INT AUTO_INCREMENT PRIMARY KEY,
                           supplier_id INT NULL,
                           medicine_id INT NOT NULL,
                           batch_id INT NOT NULL,
                           batch_number VARCHAR(50) NOT NULL,
                           quantity INT NOT NULL,
                           unit_cost DECIMAL(15,2) NOT NULL DEFAULT 0,
                           reason VARCHAR(40) NOT NULL,
                           note VARCHAR(255) NULL,
                           return_date DATE NOT NULL,
                           user_id INT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_sr_date (return_date))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS supplier_payments (
                           payment_id INT AUTO_INCREMENT PRIMARY KEY,
                           supplier_id INT NOT NULL,
                           amount DECIMAL(15,2) NOT NULL,
                           paid_on DATE NOT NULL,
                           method VARCHAR(20) NULL,
                           note VARCHAR(255) NULL,
                           user_id INT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_sp_supplier (supplier_id))""")   # v86.48: payments made to suppliers
        cur.execute("""CREATE TABLE IF NOT EXISTS cash_sessions (
                           session_id INT AUTO_INCREMENT PRIMARY KEY,
                           opened_at DATETIME NOT NULL,
                           opened_by INT NULL,
                           opening_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
                           closed_at DATETIME NULL,
                           closed_by INT NULL,
                           counted_amount DECIMAL(15,2) NULL,
                           expected_amount DECIMAL(15,2) NULL,
                           shortage DECIMAL(15,2) NULL,
                           note VARCHAR(255) NULL,
                           KEY idx_cs_open (closed_at))""")   # v86.60: cash drawer sessions
        cur.execute("""CREATE TABLE IF NOT EXISTS cash_movements (
                           movement_id INT AUTO_INCREMENT PRIMARY KEY,
                           session_id INT NOT NULL,
                           kind ENUM('in','out') NOT NULL,
                           amount DECIMAL(15,2) NOT NULL,
                           reason VARCHAR(255) NOT NULL,
                           user_id INT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_cm_session (session_id))""")   # v86.60: cash in and cash out
        cur.execute("""CREATE TABLE IF NOT EXISTS expenses (
                           expense_id INT AUTO_INCREMENT PRIMARY KEY,
                           expense_date DATE NOT NULL,
                           category VARCHAR(40) NOT NULL,
                           amount DECIMAL(15,2) NOT NULL,
                           paid_via VARCHAR(20) NOT NULL,
                           note VARCHAR(255) NULL,
                           user_id INT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_exp_date (expense_date))""")   # v86.61: shop expenses
        from pharmacy.api_auth import TABLE_SQL as _API_TOKENS_SQL
        cur.execute(_API_TOKENS_SQL)   # Sprint 3: API tokens (hashed)
        cur.execute("""CREATE TABLE IF NOT EXISTS sale_payments (
                           payment_id INT AUTO_INCREMENT PRIMARY KEY,
                           sale_id INT NOT NULL,
                           user_id INT NULL,
                           amount DECIMAL(15,2) NOT NULL,
                           method VARCHAR(20) NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_pay_sale (sale_id),
                           CONSTRAINT fk_pay_sale FOREIGN KEY (sale_id) REFERENCES sales (sale_id) ON DELETE CASCADE
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sale_returns (
                           return_id INT AUTO_INCREMENT PRIMARY KEY,
                           sale_id INT NOT NULL,
                           user_id INT NULL,
                           refund_amount DECIMAL(15,2) NOT NULL,
                           reason VARCHAR(255) NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_ret_sale (sale_id),
                           CONSTRAINT fk_ret_sale FOREIGN KEY (sale_id) REFERENCES sales (sale_id) ON DELETE CASCADE
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sale_return_items (
                           return_item_id INT AUTO_INCREMENT PRIMARY KEY,
                           return_id INT NOT NULL,
                           sale_item_id INT NOT NULL,
                           medicine_id INT NOT NULL,
                           batch_id INT NULL,
                           quantity INT NOT NULL,
                           amount DECIMAL(15,2) NOT NULL,
                           KEY idx_rit_item (sale_item_id),
                           CONSTRAINT fk_rit_return FOREIGN KEY (return_id) REFERENCES sale_returns (return_id) ON DELETE CASCADE
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS audit_log (
                           audit_id INT AUTO_INCREMENT PRIMARY KEY,
                           user_id INT NULL,
                           username VARCHAR(50) NULL,
                           action VARCHAR(40) NOT NULL,
                           entity VARCHAR(40) NULL,
                           entity_id INT NULL,
                           details VARCHAR(500) NULL,
                           ip VARCHAR(45) NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           KEY idx_audit_created (created_at),
                           KEY idx_audit_action (action)
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS app_settings (
                           setting_key VARCHAR(50) NOT NULL PRIMARY KEY,
                           setting_value VARCHAR(255) NULL,
                           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS remember_tokens (
                           token_hash CHAR(64) NOT NULL PRIMARY KEY,
                           user_id INT NOT NULL,
                           expires_at DATETIME NOT NULL,
                           created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                           INDEX idx_rt_user (user_id)
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
                           lock_key CHAR(64) NOT NULL PRIMARY KEY,
                           fail_count INT NOT NULL DEFAULT 0,
                           locked_until BIGINT NOT NULL DEFAULT 0
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        cur.execute("""CREATE TABLE IF NOT EXISTS password_resets (
                           reset_id INT AUTO_INCREMENT PRIMARY KEY,
                           user_id INT NOT NULL,
                           code_hash CHAR(64) NOT NULL,
                           expires_at DATETIME NOT NULL,
                           used TINYINT NOT NULL DEFAULT 0,
                           created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                           INDEX idx_pr_user (user_id, used)
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
        existing = set()
        cur.execute("""SELECT column_name AS n FROM information_schema.columns
                       WHERE table_schema = DATABASE() AND table_name = 'audit_log'""")
        existing = {r['n'] for r in cur.fetchall()}
        for col, ddl in AUDIT_COLUMNS.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE audit_log ADD COLUMN {col} {ddl}")
        # Step 1: manufacturers were removed. Drop the link and the table once (safe to repeat).
        cur.execute("""SELECT CONSTRAINT_NAME AS n FROM information_schema.KEY_COLUMN_USAGE
                       WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'medicines'
                         AND COLUMN_NAME = 'manufacturer_id' AND REFERENCED_TABLE_NAME IS NOT NULL""")
        for fk in cur.fetchall():
            cur.execute(f"ALTER TABLE medicines DROP FOREIGN KEY `{fk['n']}`")
        if has_col('medicines', 'manufacturer_id'):
            cur.execute("ALTER TABLE medicines DROP COLUMN manufacturer_id")
        cur.execute("DROP TABLE IF EXISTS manufacturers")
        # Phase 1 (backend): product master fields, added only when missing.
        for col, ddl in PRODUCT_COLUMNS:
            if not has_col('medicines', col):
                cur.execute(f"ALTER TABLE medicines ADD COLUMN {col} {ddl}")
        if not has_col('api_tokens', 'user_id'):          # v54: API token linked to a user (POS checkout)
            cur.execute("ALTER TABLE api_tokens ADD COLUMN user_id INT NULL")
        # v88.00: B2 - detect duplicate live barcodes FIRST (read-only). Never delete or merge rows.
        _dup_barcodes = []
        try:
            cur.execute("""SELECT barcode, GROUP_CONCAT(name ORDER BY name SEPARATOR ', ') AS names, COUNT(*) AS n
                           FROM medicines
                           WHERE is_deleted = 0 AND barcode IS NOT NULL AND barcode <> ''
                           GROUP BY barcode HAVING COUNT(*) > 1""")
            _dup_barcodes = cur.fetchall()
        except Exception:
            app.logger.exception('duplicate barcode check failed')
        for _d in _dup_barcodes:
            app.logger.warning('duplicate barcode %s on %s medicines: %s - unique index skipped until fixed',
                               _d['barcode'], _d['n'], _d['names'])
        if _dup_barcodes:
            app.logger.warning('uq_medicines_barcode NOT added: %s duplicate barcode(s). '
                               'Run database/check_duplicate_barcodes.sql to list them.', len(_dup_barcodes))
        else:
            try:                              # one barcode, one medicine
                cur.execute("ALTER TABLE medicines ADD UNIQUE INDEX uq_medicines_barcode (barcode)")
            except Exception:
                app.logger.warning('barcode unique index not added (it already exists)')
        run_migrations(cur)              # B2: numbered files in database/migrations, each runs once
        ensure_medicine_hidden_column(cur)   # v86.29: deleted medicines are hidden, their bills stay
        ensure_hidden_views(cur)             # v86.37: dashboard views skip hidden medicines
        mysql.connection.commit()
        _schema_ready = True
        ensure_audit_triggers()          # append-only protection, applied on first request too
        ensure_stock_triggers()          # v83: sale/purchase stock triggers must exist
        ensure_register_triggers(cur, app.logger)   # Phase 4: controlled register append-only
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('Database auto-update failed')
    finally:
        cur.close()

@app.before_request
def _assign_request_id():
    g.request_id = secrets.token_hex(6)

@app.after_request
def _add_request_id_header(resp):
    rid = getattr(g, 'request_id', None)
    if rid:
        resp.headers.setdefault('X-Request-ID', rid)
    return resp

# ---------- REMEMBER ME: stay logged in on this PC for 30 days (no password is stored) ----------
REMEMBER_COOKIE = 'mg_remember'
REMEMBER_DAYS = 30

def _remember_hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def remember_login(user_id):
    """New random token for this user. Only its SHA-256 hash is stored in the database."""
    token = secrets.token_urlsafe(32)
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM remember_tokens WHERE expires_at < NOW()")
        cur.execute("""INSERT INTO remember_tokens (token_hash, user_id, expires_at)
                       VALUES (%s, %s, NOW() + INTERVAL %s DAY)""", (_remember_hash(token), user_id, REMEMBER_DAYS))
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
    return token

def forget_login(token):
    if not token or len(token) > 200:
        return
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM remember_tokens WHERE token_hash = %s", (_remember_hash(token),))
        mysql.connection.commit()
    finally:
        cur.close()

def set_remember_cookie(resp, token):
    resp.set_cookie(REMEMBER_COOKIE, token, max_age=REMEMBER_DAYS * 86400, httponly=True,
                    samesite='Lax', secure=Config.SESSION_COOKIE_SECURE, path='/')
    return resp

def clear_remember_cookie(resp):
    resp.delete_cookie(REMEMBER_COOKIE, path='/', httponly=True, samesite='Lax', secure=Config.SESSION_COOKIE_SECURE)
    return resp

def _within_access_window(start_td, end_td):
    if not (isinstance(start_td, timedelta) and isinstance(end_td, timedelta)):
        return True
    now = datetime.now()
    cur_s = now.hour * 3600 + now.minute * 60 + now.second
    s, e = start_td.total_seconds(), end_td.total_seconds()
    if s <= e:
        return s <= cur_s <= e
    return cur_s >= s or cur_s <= e

@app.before_request
def _restore_remembered_login():
    """A PC with a valid 'remember me' cookie gets logged in again, without typing the password."""
    if session.get('user_id') or request.endpoint in (None, 'static', 'logout'):
        return None
    token = request.cookies.get(REMEMBER_COOKIE)
    if not token or len(token) > 200:
        return None
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("""SELECT u.user_id, u.full_name, u.access_start_time, u.access_end_time, r.role_name
                       FROM remember_tokens t
                       JOIN users u ON u.user_id = t.user_id
                       JOIN roles r ON r.role_id = u.role_id
                       WHERE t.token_hash = %s AND t.expires_at > NOW() AND u.is_active = TRUE""",
                    (_remember_hash(token),))
        row = cur.fetchone()
    except Exception:
        app.logger.exception('remember-me check failed (normal login still works)')
        return None
    finally:
        if cur:
            cur.close()
    if not row:
        app.logger.info('remember-me: cookie present but no active token (expired, logged out, or user inactive)')
        return None
    if row['role_name'] != 'Admin' and not _within_access_window(row['access_start_time'], row['access_end_time']):
        app.logger.info('remember-me: user %s is outside the access hours, login needed', row['user_id'])
        return None
    app.logger.info('remember-me: logged user %s back in from the cookie', row['user_id'])
    session.clear()
    session.permanent = True
    session['user_id'] = row['user_id']
    session['user_name'] = row['full_name']
    session['role'] = row['role_name']
    return None

@app.before_request
def _sync_session_user():
    """Keep the name and role in the session equal to the database on every page.
    Without this, a name changed in My Profile or on the Users page only showed up after a new login.
    A deactivated account is logged out at once. (A deleted account's session ends after the idle timeout.)"""
    uid = session.get('user_id')
    if not uid or request.endpoint in (None, 'static', 'login', 'logout'):
        return None
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("""SELECT u.full_name, u.is_active, r.role_name
                       FROM users u JOIN roles r ON u.role_id = r.role_id
                       WHERE u.user_id = %s""", (uid,))
        row = cur.fetchone()
    except Exception:
        app.logger.exception('could not refresh session user (page still opens)')
        return None
    finally:
        if cur:
            cur.close()
    if row is None:          # no answer from the database: keep the session as it is
        return None
    if 'is_active' in row and not row['is_active']:
        session.clear()
        flash('Your account is deactivated. Please contact the admin.', 'warning')
        return redirect(url_for('login'))
    if row.get('full_name'):
        session['user_name'] = row['full_name']
    if row.get('role_name'):
        session['role'] = row['role_name']
    return None

@app.before_request
def _schema_once():
    if not _schema_ready and request.endpoint not in ('static', None):
        try:
            ensure_schema()
        except Exception:
            g.db_down = True                       # pages still open; a banner tells the user what to check
            app.logger.exception('database not reachable during start-up check')

# ---------- DECORATORS ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _reset_hash(code):
    """Password-reset codes are stored only as a hash. Input is normalised: no dashes, no spaces, upper case."""
    clean = re.sub(r'[\s-]', '', code or '').upper()
    return hashlib.sha256(clean.encode('utf-8')).hexdigest()
