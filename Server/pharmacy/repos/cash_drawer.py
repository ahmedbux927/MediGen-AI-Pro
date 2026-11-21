"""SQL for the cash drawer (v86.60). Writes only to cash_sessions and cash_movements."""


def open_session(cur):
    cur.execute("SELECT * FROM cash_sessions WHERE closed_at IS NULL ORDER BY session_id DESC LIMIT 1")
    return cur.fetchone()


def insert_session(cur, opening, user_id):
    cur.execute("""INSERT INTO cash_sessions (opened_at, opened_by, opening_amount)
                   VALUES (NOW(), %s, %s)""", (user_id, opening))
    return cur.lastrowid


def session_by_id(cur, sid):
    cur.execute("SELECT * FROM cash_sessions WHERE session_id = %s", (sid,))
    return cur.fetchone()


def cash_sales_since(cur, since):
    """v86.61: all cash received since the drawer opened: cash paid at a sale and udhaar repaid in cash.
    Both are written to sale_payments, so nothing is counted twice."""
    cur.execute("""SELECT COALESCE(SUM(amount), 0) AS v FROM sale_payments
                   WHERE method = 'Cash' AND created_at >= %s""", (since,))
    return float(cur.fetchone()['v'] or 0)


def cash_refunds_since(cur, since):
    cur.execute("""SELECT COALESCE(SUM(r.refund_amount), 0) AS v
                   FROM sale_returns r JOIN sales s ON s.sale_id = r.sale_id
                   WHERE s.payment_method = 'Cash' AND r.created_at >= %s""", (since,))
    return float(cur.fetchone()['v'] or 0)


def movement_totals(cur, sid):
    cur.execute("""SELECT COALESCE(SUM(CASE WHEN kind='in' THEN amount ELSE 0 END), 0) AS cin,
                          COALESCE(SUM(CASE WHEN kind='out' THEN amount ELSE 0 END), 0) AS cout
                   FROM cash_movements WHERE session_id = %s""", (sid,))
    r = cur.fetchone()
    return float(r['cin'] or 0), float(r['cout'] or 0)


def insert_movement(cur, sid, kind, amount, reason, user_id):
    cur.execute("""INSERT INTO cash_movements (session_id, kind, amount, reason, user_id)
                   VALUES (%s, %s, %s, %s, %s)""", (sid, kind, amount, reason, user_id))
    return cur.lastrowid


def movements(cur, sid):
    cur.execute("""SELECT m.kind, m.amount, m.reason, m.created_at, u.username
                   FROM cash_movements m LEFT JOIN users u ON u.user_id = m.user_id
                   WHERE m.session_id = %s ORDER BY m.movement_id DESC LIMIT 200""", (sid,))
    return cur.fetchall()


def close_session(cur, sid, counted, expected, diff, user_id, note):
    cur.execute("""UPDATE cash_sessions SET closed_at = NOW(), closed_by = %s, counted_amount = %s,
                   expected_amount = %s, shortage = %s, note = %s
                   WHERE session_id = %s AND closed_at IS NULL""",
                (user_id, counted, expected, diff, note, sid))
    return cur.rowcount


def history(cur, limit=14):
    cur.execute("""SELECT c.session_id, c.opened_at, c.closed_at, c.opening_amount, c.expected_amount,
                          c.counted_amount, c.shortage, u1.username AS opened_by, u2.username AS closed_by
                   FROM cash_sessions c
                   LEFT JOIN users u1 ON u1.user_id = c.opened_by
                   LEFT JOIN users u2 ON u2.user_id = c.closed_by
                   ORDER BY c.session_id DESC LIMIT %s""", (limit,))
    return cur.fetchall()
