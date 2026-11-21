"""SQL for the Supplier Summary (v86.47). Read only."""


def supplier_totals(cur):
    cur.execute("""SELECT s.supplier_id, s.name, s.contact,
                          COUNT(po.po_id) AS orders,
                          COALESCE(SUM(po.status = 'Received'), 0) AS received,
                          COALESCE(SUM(po.status = 'Pending'), 0) AS pending,
                          COALESCE(SUM(CASE WHEN po.status = 'Received' THEN po.total_amount ELSE 0 END), 0) AS bought,
                          MAX(po.delivery_date) AS last_delivery
                   FROM suppliers s
                   LEFT JOIN purchase_orders po ON po.supplier_id = s.supplier_id
                   GROUP BY s.supplier_id, s.name, s.contact
                   ORDER BY bought DESC, s.name""")
    return cur.fetchall()


def returns_by_supplier(cur):
    cur.execute("""SELECT supplier_id, COALESCE(SUM(quantity * unit_cost), 0) AS returned
                   FROM supplier_returns WHERE supplier_id IS NOT NULL GROUP BY supplier_id""")
    return {r['supplier_id']: float(r['returned'] or 0) for r in cur.fetchall()}


def paid_by_supplier(cur):
    cur.execute("""SELECT supplier_id, COALESCE(SUM(amount), 0) AS paid
                   FROM supplier_payments GROUP BY supplier_id""")
    return {r['supplier_id']: float(r['paid'] or 0) for r in cur.fetchall()}


def recent_payments(cur, limit=30):
    cur.execute("""SELECT p.payment_id, p.paid_on, p.amount, p.method, p.note, s.name AS supplier_name
                   FROM supplier_payments p JOIN suppliers s ON s.supplier_id = p.supplier_id
                   ORDER BY p.paid_on DESC, p.payment_id DESC LIMIT %s""", (limit,))
    return cur.fetchall()


def supplier_exists(cur, supplier_id):
    cur.execute("SELECT 1 FROM suppliers WHERE supplier_id = %s", (supplier_id,))
    return cur.fetchone() is not None


def insert_payment(cur, supplier_id, amount, paid_on, method, note, user_id):
    cur.execute("""INSERT INTO supplier_payments (supplier_id, amount, paid_on, method, note, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""", (supplier_id, amount, paid_on, method, note, user_id))
    return cur.lastrowid
