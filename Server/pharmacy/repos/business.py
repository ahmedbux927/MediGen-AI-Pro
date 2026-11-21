"""SQL for daily closing and customer dues."""


def daily_closing(cur, day):
    """Totals for one calendar day (YYYY-MM-DD)."""
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(total_amount), 0) AS gross,
                          IFNULL(SUM(total_amount - returned_amount - paid_amount), 0) AS new_dues
                   FROM sales WHERE DATE(sale_date) = %s""", (day,))
    sales = cur.fetchone() or {}
    cur.execute("""SELECT IFNULL(SUM(si.quantity), 0) AS units
                   FROM sale_items si JOIN sales s ON si.sale_id = s.sale_id
                   WHERE DATE(s.sale_date) = %s""", (day,))
    units = (cur.fetchone() or {}).get('units', 0)
    cur.execute("""SELECT method, IFNULL(SUM(amount), 0) AS total
                   FROM sale_payments WHERE DATE(created_at) = %s GROUP BY method""", (day,))
    by_method = {r['method']: float(r['total']) for r in cur.fetchall()}
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(refund_amount), 0) AS refunds
                   FROM sale_returns WHERE DATE(created_at) = %s""", (day,))
    ret = cur.fetchone() or {}
    return {
        'sales_count': int(sales.get('n') or 0),
        'gross': float(sales.get('gross') or 0),
        'new_dues': float(sales.get('new_dues') or 0),
        'units': int(units or 0),
        'by_method': by_method,
        'returns_count': int(ret.get('n') or 0),
        'refunds': float(ret.get('refunds') or 0),
    }


def customers_with_dues(cur):
    """Customers who still owe money on at least one sale, biggest debt first."""
    cur.execute("""SELECT c.customer_id, c.name, c.contact_number,
                          SUM(s.total_amount - s.returned_amount - s.paid_amount) AS due,
                          MIN(s.sale_date) AS oldest_sale
                   FROM sales s JOIN customers c ON s.customer_id = c.customer_id
                   WHERE s.total_amount - s.returned_amount - s.paid_amount > 0.004
                   GROUP BY c.customer_id, c.name, c.contact_number
                   ORDER BY due DESC""")
    return cur.fetchall()
