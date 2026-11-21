"""v86.76: one record set per product section for the dashboard.

Every number is for one section (Medicines, Syrups & Suspensions, Creams & Gels,
Drip & Injection, Bandages & Other). The day is the shop PC date, so "today"
starts again at 12:00 AM with no manual reset.
"""
from datetime import date, timedelta
from pharmacy.services import product_sections as PS


def _empty(key, label, icon):
    return {'key': key, 'label': label, 'icon': icon,
            'items': 0, 'in_stock': 0, 'low': 0, 'out': 0, 'expiring': 0,
            'sold_today': 0, 'sales_today': 0.0, 'cost_today': 0.0, 'profit_today': 0.0,
            'sold_month': 0, 'sales_month': 0.0, 'cost_month': 0.0, 'profit_month': 0.0,
            'purchase_today': 0.0, 'purchase_month': 0.0, 'customers_month': 0, 'customers_all': 0, 'no_price': 0,
            'top': [], 'low_items': [], 'expiring_items': []}


def build(cur, today=None):
    """Returns {'sections': [...per section...], 'totals': {...}, 'week': {...}, 'day': iso}."""
    from pharmacy.routes.reports import _section_rows   # same rule as the Reports page

    today = today or date.today()
    day = today.isoformat()
    month = today.replace(day=1).isoformat()
    week_start = today - timedelta(days=6)
    thirty_start = today - timedelta(days=29)
    exp_end = today + timedelta(days=90)

    secs = {k: _empty(k, lab, ic) for k, lab, ic, _d in PS.SECTIONS}
    order = [k for k, _l, _i, _d in PS.SECTIONS]

    # 1. stock counts per section (items, in stock, low, out) from the shared overview
    ov = PS.overview(cur)
    for k in order:
        for f in ('items', 'in_stock', 'low', 'out'):
            secs[k][f] = ov[k].get(f, 0)

    # 2. low stock items (names), per section
    cur.execute("""SELECT name, dosage_form, stock_quantity, reorder_level FROM medicines
                   WHERE is_deleted = 0 AND stock_quantity <= reorder_level ORDER BY stock_quantity, name""")
    for r in cur.fetchall():
        k = PS.section_for(r['dosage_form'])
        secs[k]['low_items'].append({'name': r['name'], 'stock': int(r['stock_quantity'] or 0),
                                     'reorder': int(r['reorder_level'] or 0)})

    # 3. batches expiring within 90 days, per section (earliest first)
    cur.execute("""SELECT m.name, m.dosage_form, b.batch_number, b.expiry_date, b.quantity
                   FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0 AND b.quantity > 0
                     AND b.expiry_date BETWEEN %s AND %s
                   ORDER BY b.expiry_date, m.name""", (day, exp_end.isoformat()))
    for r in cur.fetchall():
        k = PS.section_for(r['dosage_form'])
        secs[k]['expiring'] += 1
        secs[k]['expiring_items'].append({'name': r['name'], 'batch': r['batch_number'] or '-',
                                          'expiry': r['expiry_date'].strftime('%d %b %Y') if r['expiry_date'] else '',
                                          'days': (r['expiry_date'] - today).days if r['expiry_date'] else 0,
                                          'qty': int(r['quantity'] or 0)})

    # 4. best sellers of the last 30 days, per section, net of returns
    cur.execute("""SELECT m.name, m.dosage_form,
                          SUM(si.quantity - IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                                    WHERE ri.sale_item_id = si.sale_item_id), 0)) AS sold,
                          SUM(si.subtotal) AS revenue
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   JOIN medicines m ON si.medicine_id = m.medicine_id
                   WHERE DATE(s.sale_date) BETWEEN %s AND %s
                   GROUP BY m.medicine_id, m.name, m.dosage_form
                   HAVING sold > 0
                   ORDER BY sold DESC, m.name""", (thirty_start.isoformat(), day))
    for r in cur.fetchall():
        k = PS.section_for(r['dosage_form'])
        if len(secs[k]['top']) < 5:
            secs[k]['top'].append({'name': r['name'], 'sold': int(r['sold']),
                                   'revenue': float(r['revenue'] or 0)})

    # 5. sales, cost and profit per section: today and this month (returns taken out)
    for row in _section_rows(cur, day, day):
        s = secs[row['key']]
        s['sold_today'], s['sales_today'] = row['sold'], row['revenue']
        s['cost_today'], s['profit_today'] = row['cost'], row['profit']
    for row in _section_rows(cur, month, day):
        s = secs[row['key']]
        s['sold_month'], s['sales_month'] = row['sold'], row['revenue']
        s['cost_month'], s['profit_month'] = row['cost'], row['profit']

    # 6. purchases (stock received) per section: today and this month
    cur.execute("""SELECT m.dosage_form, po.order_date, pi.quantity, pi.unit_price
                   FROM purchase_items pi
                   JOIN purchase_orders po ON pi.po_id = po.po_id
                   JOIN medicines m ON pi.medicine_id = m.medicine_id
                   WHERE po.order_date BETWEEN %s AND %s""", (month, day))
    for r in cur.fetchall():
        k = PS.section_for(r['dosage_form'])
        amount = float(r['quantity'] or 0) * float(r['unit_price'] or 0)
        secs[k]['purchase_month'] += amount
        if r['order_date'] == today:
            secs[k]['purchase_today'] += amount

    # 7. customers per section this month (distinct, walk-in customers not counted)
    cur.execute("""SELECT m.dosage_form, s.customer_id
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   JOIN medicines m ON si.medicine_id = m.medicine_id
                   WHERE s.customer_id IS NOT NULL AND DATE(s.sale_date) BETWEEN %s AND %s
                   GROUP BY m.dosage_form, s.customer_id""", (month, day))
    seen = {k: set() for k in order}
    for r in cur.fetchall():
        seen[PS.section_for(r['dosage_form'])].add(r['customer_id'])
    for k in order:
        secs[k]['customers_month'] = len(seen[k])

    # 7b. customers per section, all time (distinct, walk-in not counted)
    cur.execute("""SELECT m.dosage_form, s.customer_id
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   JOIN medicines m ON si.medicine_id = m.medicine_id
                   WHERE s.customer_id IS NOT NULL
                   GROUP BY m.dosage_form, s.customer_id""")
    everyone = {k: set() for k in order}
    for r in cur.fetchall():
        everyone[PS.section_for(r['dosage_form'])].add(r['customer_id'])
    for k in order:
        secs[k]['customers_all'] = len(everyone[k])

    # 7c. medicines with price 0 or no price (billing would be wrong), per section
    cur.execute("""SELECT dosage_form FROM medicines
                   WHERE is_deleted = 0 AND (price IS NULL OR price <= 0)""")
    no_price = 0
    for r in cur.fetchall():
        secs[PS.section_for(r['dosage_form'])]['no_price'] = secs[PS.section_for(r['dosage_form'])].get('no_price', 0) + 1
        no_price += 1

    # 8. last 7 days: sales and purchases for the whole shop (chart)
    cur.execute("""SELECT DATE(sale_date) AS d, IFNULL(SUM(total_amount - returned_amount), 0) AS rev
                   FROM sales WHERE DATE(sale_date) BETWEEN %s AND %s GROUP BY DATE(sale_date)""",
                (week_start.isoformat(), day))
    sales_by_day = {r['d'].isoformat(): float(r['rev'] or 0) for r in cur.fetchall()}
    cur.execute("""SELECT po.order_date AS d, IFNULL(SUM(pi.quantity * pi.unit_price), 0) AS amt
                   FROM purchase_items pi JOIN purchase_orders po ON pi.po_id = po.po_id
                   WHERE po.order_date BETWEEN %s AND %s GROUP BY po.order_date""",
                (week_start.isoformat(), day))
    buy_by_day = {r['d'].isoformat(): float(r['amt'] or 0) for r in cur.fetchall()}
    days = [(week_start + timedelta(days=i)) for i in range(7)]
    week = {'days': [d.strftime('%d %b') for d in days],
            'sales': [round(sales_by_day.get(d.isoformat(), 0.0), 2) for d in days],
            'purchases': [round(buy_by_day.get(d.isoformat(), 0.0), 2) for d in days]}

    # 9. totals for the header cards
    sections = [secs[k] for k in order]
    totals = {f: sum(s[f] for s in sections) for f in
              ('items', 'in_stock', 'low', 'out', 'expiring', 'sold_today', 'sales_today', 'cost_today',
               'profit_today', 'sold_month', 'sales_month', 'cost_month', 'profit_month',
               'purchase_today', 'purchase_month')}
    totals['customers_month'] = len(set().union(*seen.values())) if seen else 0
    totals['no_price'] = no_price
    totals['customers_all'] = len(set().union(*everyone.values())) if everyone else 0
    scale = max([max(s['sales_month'], s['purchase_month']) for s in sections] + [1.0])
    for s in sections:
        s['share'] = round(s['sales_month'] * 100 / scale, 1)
        s['purchase_share'] = round(s['purchase_month'] * 100 / scale, 1)
    return {'sections': sections, 'totals': totals, 'week': week, 'day': day}
