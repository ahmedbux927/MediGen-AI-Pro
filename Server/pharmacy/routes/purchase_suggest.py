"""Routes: purchase suggestions (v86.24). Suggests how many units to order, from the last 30 days of sales.
Suggestion only: nothing is ordered automatically. Staff create the order on the Purchase page."""
import math

from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _csv_response
from flask import make_response

SALES_DAYS = 30        # look-back window for the sale rate
COVER_DAYS = 30        # order enough for this many days
ALERT_DAYS = 14        # show an item when stock lasts fewer days than this


def _suggestion_rows(cur):
    cur.execute("""SELECT m.medicine_id, m.name, m.stock_quantity, m.reorder_level, m.cost_price,
                          IFNULL((SELECT SUM(si.quantity - IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                                                    WHERE ri.sale_item_id = si.sale_item_id), 0))
                                  FROM sale_items si JOIN sales s ON si.sale_id = s.sale_id
                                  WHERE si.medicine_id = m.medicine_id
                                    AND DATE(s.sale_date) >= CURDATE() - INTERVAL %s DAY), 0) AS sold
                   FROM medicines m WHERE m.is_deleted = 0""", (SALES_DAYS,))
    rows = []
    for m in cur.fetchall():
        stock = int(m['stock_quantity'] or 0)
        reorder = int(m['reorder_level'] or 0)
        sold = max(0, int(m['sold'] or 0))
        daily = sold / SALES_DAYS
        days_left = (stock / daily) if daily > 0 else None
        low = stock <= reorder
        running_out = days_left is not None and days_left < ALERT_DAYS
        if not (low or running_out):
            continue
        target = max(math.ceil(daily * COVER_DAYS), reorder)
        qty = max(0, target - stock)
        if qty == 0:
            continue
        cost = float(m['cost_price'] or 0)
        rows.append({'medicine_id': m.get('medicine_id'), 'cost': cost, 'name': m['name'], 'stock': stock, 'reorder': reorder, 'sold': sold,
                     'days_left': None if days_left is None else round(days_left, 1),
                     'qty': qty, 'est_cost': round(qty * cost, 2), 'low': low})
    rows.sort(key=lambda r: (r['days_left'] is None, r['days_left'] or 0, r['name']))
    return rows


@app.route('/purchase/suggestions')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def purchase_suggestions():
    cur = mysql.connection.cursor()
    try:
        rows = _suggestion_rows(cur)
        if request.args.get('fmt') == 'csv':
            return _csv_response(['Medicine', 'Stock', 'Reorder level', f'Sold last {SALES_DAYS} days',
                                  'Days left', 'Suggested qty', 'Est. cost (Rs.)'],
                                 [(r['name'], r['stock'], r['reorder'], r['sold'],
                                   '' if r['days_left'] is None else r['days_left'],
                                   r['qty'], r['est_cost']) for r in rows],
                                 f'purchase_suggestions_{date.today().isoformat()}.csv')
        resp = make_response(render_template('purchase_suggest.html', rows=rows, sales_days=SALES_DAYS,
                                             cover_days=COVER_DAYS, alert_days=ALERT_DAYS,
                                             total_cost=round(sum(r['est_cost'] for r in rows), 2)))
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    finally:
        cur.close()
