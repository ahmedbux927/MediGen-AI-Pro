"""Rules for deleting a user (v78). No Flask.

- Login-only rows (remember tokens, reset codes, API tokens) are always removed with the user.
- Any other table that has a user_id column is a record of work done (sales, stock changes, audit lines...).
  If such rows exist, the account is turned OFF instead of deleted, so the history keeps the name.
"""
LOGIN_TABLES = ('remember_tokens', 'password_resets', 'api_tokens')
# Audit lines are not work history: every login writes one. They keep the username as text anyway.
NOT_HISTORY = ('audit_log',)
LABELS = {
    'sales': 'sales', 'chat_history': 'chat messages', 'stock_adjustments': 'stock changes',
    'audit_log': 'audit entries', 'drip_injections': 'drip/injection records',
    'agent_actions': 'assistant actions', 'purchase_orders': 'purchase orders',
    'supplier_returns': 'supplier returns', 'batches': 'batches', 'prescriptions': 'prescriptions',
}


def history_tables(cur):
    """Names of tables (other than users and login tables) that have a user_id column."""
    cur.execute("""SELECT TABLE_NAME FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME = 'user_id'""")
    names = [r['TABLE_NAME'] for r in cur.fetchall()]
    return [t for t in names if t != 'users' and t not in LOGIN_TABLES and t not in NOT_HISTORY]


def history_counts(cur, uid):
    """{table: rows} for everything this user did. Table names come from information_schema, never from the user."""
    counts = {}
    for t in history_tables(cur):
        cur.execute(f"SELECT COUNT(*) AS n FROM `{t}` WHERE user_id = %s", (uid,))
        n = int((cur.fetchone() or {}).get('n') or 0)
        if n:
            counts[t] = n
    return counts


def summary(counts):
    """Plain sentence for the admin, e.g. '12 sales, 3 stock changes'."""
    parts = [f"{n} {LABELS.get(t, t.replace('_', ' '))}" for t, n in sorted(counts.items(), key=lambda kv: -kv[1])]
    return ', '.join(parts)


# --- v101.03: permanent delete -------------------------------------------------
# The history scan above watches columns NAMED user_id. A few tables point at a
# user through a differently named column (stock_counts.counted_by /
# approved_by, purchase_drafts.created_by). The definitive list of what can
# block a DELETE is the foreign keys themselves, so read those too.

def fk_references(cur):
    """Every (table, column) holding a real FOREIGN KEY to users.user_id."""
    cur.execute("""SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
                   WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME = 'users'
                     AND REFERENCED_COLUMN_NAME = 'user_id'""")
    return [(r['TABLE_NAME'], r['COLUMN_NAME']) for r in cur.fetchall()]


def all_references(cur, uid):
    """{table: rows} for EVERY row pointing at this user: the user_id history
    scan plus every foreign-key column, whatever it is named."""
    counts = dict(history_counts(cur, uid))
    for t, col in fk_references(cur):
        if col == 'user_id' or t in NOT_HISTORY:
            continue  # already counted; audit lines keep the username as text
        cur.execute(f"SELECT COUNT(*) AS n FROM `{t}` WHERE `{col}` = %s", (uid,))
        n = int((cur.fetchone() or {}).get('n') or 0)
        if n:
            counts[t] = counts.get(t, 0) + n
    return counts


def placeholder_user(cur):
    """The 'Deleted user' account that inherits a permanently deleted user's
    records, so sales and stock history (legal records) survive while the
    person is gone. Inactive, with a password nobody can know. Returns its id."""
    cur.execute("SELECT user_id FROM users WHERE username = 'deleted-user'")
    row = cur.fetchone()
    if row:
        return row['user_id']
    import secrets as _secrets
    import bcrypt as _bcrypt
    cur.execute("SELECT role_id FROM roles ORDER BY role_id LIMIT 1")
    role_id = cur.fetchone()['role_id']
    pw_hash = _bcrypt.hashpw(_secrets.token_bytes(32), _bcrypt.gensalt()).decode()
    cur.execute("""INSERT INTO users (full_name, username, password_hash, role_id, is_active)
                   VALUES ('Deleted user', 'deleted-user', %s, %s, 0)""", (pw_hash, role_id))
    return cur.lastrowid


def reassign_references(cur, from_uid, to_uid):
    """Point every row that references from_uid at to_uid instead: all user_id
    history columns and every foreign-key column, whatever it is named."""
    done = set()
    for t in history_tables(cur):
        cur.execute(f"UPDATE `{t}` SET user_id = %s WHERE user_id = %s", (to_uid, from_uid))
        done.add((t, 'user_id'))
    for t, col in fk_references(cur):
        if (t, col) in done:
            continue
        cur.execute(f"UPDATE `{t}` SET `{col}` = %s WHERE `{col}` = %s", (to_uid, from_uid))
