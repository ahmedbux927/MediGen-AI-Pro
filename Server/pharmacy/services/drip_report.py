"""v85: drip and injection reports for the dashboard and the records page. Read-only SQL. Callers pass a cursor.

- Drip medicines = dosage form that is an injection or drip (same rule as the sale screen).
- Expiry is checked per batch (batches hold the real expiry dates and quantities).
"""
from pharmacy.services import drip_record as DR

EXPIRY_WINDOW_DAYS = 90


def drip_medicine_ids(cur):
    cur.execute("SELECT medicine_id, dosage_form FROM medicines WHERE is_deleted = 0")
    return [r['medicine_id'] for r in cur.fetchall() if DR.is_drip_form(r['dosage_form'])]


def _in_clause(ids):
    return ','.join(['%s'] * len(ids))


def summary(cur):
    """Numbers for the dashboard tile. Safe when no drip item exists yet."""
    DR.ensure_drip_table(cur)
    ids = drip_medicine_ids(cur)
    out = {'items': len(ids), 'in_stock': 0, 'no_stock': 0, 'low_stock': 0,
           'today_records': 0, 'today_qty': 0, 'month_records': 0,
           'expiring': 0, 'expired_qty': 0, 'expiring_window': EXPIRY_WINDOW_DAYS}
    if ids:
        cur.execute(f"""SELECT medicine_id, stock_quantity, reorder_level FROM medicines
                        WHERE medicine_id IN ({_in_clause(ids)})""", tuple(ids))
        for r in cur.fetchall():
            qty = int(r['stock_quantity'] or 0)
            if qty > 0:
                out['in_stock'] += 1
                if qty <= int(r['reorder_level'] or 0):
                    out['low_stock'] += 1
            else:
                out['no_stock'] += 1
        cur.execute(f"""SELECT COUNT(*) AS n FROM batches
                        WHERE medicine_id IN ({_in_clause(ids)}) AND quantity > 0
                          AND expiry_date BETWEEN CURDATE() AND CURDATE() + INTERVAL {EXPIRY_WINDOW_DAYS} DAY""", tuple(ids))
        out['expiring'] = int(cur.fetchone()['n'] or 0)
        cur.execute(f"""SELECT IFNULL(SUM(quantity),0) AS q FROM batches
                        WHERE medicine_id IN ({_in_clause(ids)}) AND quantity > 0 AND expiry_date < CURDATE()""", tuple(ids))
        out['expired_qty'] = int(cur.fetchone()['q'] or 0)
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(quantity),0) AS q FROM drip_injections
                   WHERE DATE(given_at) = CURDATE()""")
    row = cur.fetchone()
    out['today_records'], out['today_qty'] = int(row['n'] or 0), int(row['q'] or 0)
    cur.execute("""SELECT COUNT(*) AS n FROM drip_injections
                   WHERE YEAR(given_at)=YEAR(CURDATE()) AND MONTH(given_at)=MONTH(CURDATE())""")
    out['month_records'] = int(cur.fetchone()['n'] or 0)
    return out


def expiring_batches(cur, days=EXPIRY_WINDOW_DAYS):
    """Drip batches with stock that expire within `days`, plus expired ones still holding stock (oldest first)."""
    ids = drip_medicine_ids(cur)
    if not ids:
        return []
    cur.execute(f"""SELECT b.batch_id, b.batch_number, b.quantity, b.expiry_date, m.name, m.medicine_id,
                           DATEDIFF(b.expiry_date, CURDATE()) AS days_left
                    FROM batches b JOIN medicines m ON m.medicine_id = b.medicine_id
                    WHERE b.medicine_id IN ({_in_clause(ids)}) AND b.quantity > 0
                      AND b.expiry_date <= CURDATE() + INTERVAL %s DAY
                    ORDER BY b.expiry_date""", tuple(ids) + (int(days),))
    return cur.fetchall()


def records(cur, date_from, date_to, limit=1000):
    """Drip and injection records between two dates (inclusive), newest first."""
    DR.ensure_drip_table(cur)
    cur.execute("""SELECT d.record_id, d.given_at, m.name AS medicine_name, d.route, d.dose_text, d.quantity,
                          d.sale_id, d.notes, IFNULL(c.name, 'Walk-in') AS patient, u.full_name AS given_by_name
                   FROM drip_injections d
                   JOIN medicines m ON m.medicine_id = d.medicine_id
                   LEFT JOIN customers c ON c.customer_id = d.customer_id
                   LEFT JOIN users u ON u.user_id = d.given_by
                   WHERE DATE(d.given_at) BETWEEN %s AND %s
                   ORDER BY d.given_at DESC LIMIT %s""", (date_from, date_to, int(limit)))
    return cur.fetchall()
