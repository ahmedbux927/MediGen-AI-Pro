"""AI agent tool layer (v54). No Flask, no HTTP. The caller passes the cursor, the user id and the time.

READ tools only SELECT. Nothing they return is a command.
WRITE actions are two steps:
  1. propose(...)  stores the requested change and returns a one-time confirmation token (valid 5 minutes).
                   The agent must show the summary to the user and ask.
  2. confirm(...)  runs the change only when the SAME user sends the token back. The token works once.
Only whitelisted actions exist. Anything else is refused.
Times are naive local datetimes (the same clock as the database NOW()).
"""
import hashlib
import json
import secrets
from datetime import timedelta

from pharmacy.services import inventory as INV
from pharmacy.services import phone_search as PS

CONFIRM_MINUTES = 5
MAX_ROWS = 50


class AgentError(ValueError):
    """Shown to the user as it is."""


_agent_table_ready = False


def ensure_agent_table(cur):
    """Create agent_actions once (same definition as database/migrations/007_agent_actions.sql)."""
    global _agent_table_ready
    if _agent_table_ready:
        return
    cur.execute("""CREATE TABLE IF NOT EXISTS agent_actions (
        action_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        token_hash CHAR(64) NOT NULL,
        user_id INT NOT NULL,
        action VARCHAR(40) NOT NULL,
        params TEXT NOT NULL,
        summary VARCHAR(255) NOT NULL,
        status ENUM('pending','done','cancelled') NOT NULL DEFAULT 'pending',
        expires_at DATETIME NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_agent_token (token_hash),
        KEY idx_agent_user (user_id, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    _agent_table_ready = True


def _hash(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


# ------------------------------------------------------------------ READ tools (SELECT only)
def find_medicine(cur, text, limit=10):
    """By barcode (digits, 8 or more) or by part of the name. Includes shelf location and schedule."""
    text = (text or '').strip()
    if not text:
        return []
    limit = min(max(1, int(limit)), 20)
    if text.isdigit() and len(text) >= 8:
        cur.execute("""SELECT medicine_id, name, barcode, stock_quantity, price, rack_location, schedule
                       FROM medicines WHERE barcode = %s AND is_deleted = 0 LIMIT %s""", (text, limit))
    else:
        cur.execute("""SELECT medicine_id, name, barcode, stock_quantity, price, rack_location, schedule
                       FROM medicines WHERE is_deleted = 0 AND LOWER(name) LIKE %s ORDER BY name LIMIT %s""",
                    ('%' + text.lower() + '%', limit))
    return cur.fetchall()


def low_stock(cur):
    cur.execute("SELECT medicine_id, name, stock_quantity, reorder_level FROM medicines WHERE is_deleted = 0")
    return INV.low_stock(cur.fetchall())


def expiring(cur, today, days=30):
    days = min(max(1, int(days)), 365)
    cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity
                   FROM batches b JOIN medicines m ON m.medicine_id = b.medicine_id AND m.is_deleted = 0
                   WHERE b.quantity > 0 AND b.expiry_date <= DATE_ADD(%s, INTERVAL %s DAY)
                   ORDER BY b.expiry_date LIMIT %s""", (today, days, MAX_ROWS))
    return cur.fetchall()


def today_summary(cur, today):
    cur.execute("""SELECT COUNT(*) AS invoices,
                          IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
                   FROM sales WHERE DATE(sale_date) = %s""", (today,))
    row = cur.fetchone()
    return {'date': today.isoformat(), 'invoices': int(row['invoices']), 'revenue': float(row['revenue'] or 0)}


def find_customer(cur, text, limit=10):
    return PS.search_customers(cur, text, limit)


# ------------------------------------------------------------------ WRITE actions (whitelist)
ACTIONS = {
    'set_shelf_location': {'label': 'Set shelf location', 'required': ('medicine_id', 'shelf_location')},
    'add_customer': {'label': 'Add customer', 'required': ('name',)},
}


def _validate(action, params):
    if action not in ACTIONS:
        raise AgentError('This action is not allowed for the agent.')
    if not isinstance(params, dict):
        raise AgentError('Parameters must be an object.')
    missing = [k for k in ACTIONS[action]['required'] if params.get(k) in (None, '')]
    if missing:
        raise AgentError('Missing: ' + ', '.join(missing))
    if action == 'set_shelf_location':
        try:
            mid = int(params['medicine_id'])
        except (TypeError, ValueError):
            raise AgentError('medicine_id must be a number.')
        return {'medicine_id': mid, 'shelf_location': str(params['shelf_location']).strip()[:40]}
    if action == 'add_customer':
        contact = str(params.get('contact_number') or '').strip()[:15] or None
        return {'name': str(params['name']).strip()[:100], 'contact_number': contact}
    raise AgentError('This action is not allowed for the agent.')   # unreachable: whitelist above


def _summary(action, clean):
    if action == 'set_shelf_location':
        return f"Set shelf location of medicine #{clean['medicine_id']} to '{clean['shelf_location']}'"
    return f"Add customer '{clean['name']}'" + (f" ({clean['contact_number']})" if clean['contact_number'] else '')


def propose(cur, user_id, action, params, now):
    """Store the change. Returns {'token', 'summary', 'expires_at'}. The token is shown once."""
    clean = _validate(action, params)
    summary = _summary(action, clean)
    raw = 'agt_' + secrets.token_urlsafe(18)
    expires = now + timedelta(minutes=CONFIRM_MINUTES)
    # one open proposal per user: a new one replaces the old
    cur.execute("UPDATE agent_actions SET status = 'cancelled' WHERE user_id = %s AND status = 'pending'", (user_id,))
    cur.execute("""INSERT INTO agent_actions (token_hash, user_id, action, params, summary, status, expires_at)
                   VALUES (%s, %s, %s, %s, %s, 'pending', %s)""",
                (_hash(raw), user_id, action, json.dumps(clean), summary[:255], expires))
    return {'token': raw, 'summary': summary, 'expires_at': expires.isoformat(timespec='seconds')}


def _set_shelf(cur, p, audit_fn):
    cur.execute("UPDATE medicines SET rack_location = %s WHERE medicine_id = %s", (p['shelf_location'], p['medicine_id']))
    if cur.rowcount == 0:
        raise AgentError('Medicine not found.')
    audit_fn(cur, 'agent.shelf_location', 'medicine', p['medicine_id'], p['shelf_location'])
    return {'medicine_id': p['medicine_id'], 'shelf_location': p['shelf_location']}


def _add_customer(cur, p, audit_fn):
    cur.execute("INSERT INTO customers (name, contact_number) VALUES (%s, %s)", (p['name'], p['contact_number']))
    new_id = cur.lastrowid
    audit_fn(cur, 'agent.customer_add', 'customer', new_id, p['name'])
    return {'customer_id': new_id}


EXECUTORS = {'set_shelf_location': _set_shelf, 'add_customer': _add_customer}


def confirm(cur, user_id, raw, now, audit_fn):
    """Run the proposed change. The caller commits on success and rolls back on any error."""
    if not isinstance(raw, str) or not raw.startswith('agt_'):
        raise AgentError('Invalid confirmation token.')
    cur.execute("""SELECT action_id, user_id, action, params, status, expires_at
                   FROM agent_actions WHERE token_hash = %s FOR UPDATE""", (_hash(raw),))
    row = cur.fetchone()
    if not row or row['user_id'] != user_id:
        raise AgentError('Invalid confirmation token.')          # same message: do not reveal other users' tokens
    if row['status'] != 'pending':
        raise AgentError('This confirmation was already used or cancelled.')
    if row['expires_at'] < now:
        cur.execute("UPDATE agent_actions SET status = 'cancelled' WHERE action_id = %s", (row['action_id'],))
        raise AgentError('The confirmation expired. Please ask again.')
    cur.execute("UPDATE agent_actions SET status = 'done' WHERE action_id = %s AND status = 'pending'",
                (row['action_id'],))
    if cur.rowcount != 1:
        raise AgentError('This confirmation was already used.')
    params = json.loads(row['params'])
    result = EXECUTORS[row['action']](cur, params, audit_fn)
    return {'action': row['action'], 'result': result}
