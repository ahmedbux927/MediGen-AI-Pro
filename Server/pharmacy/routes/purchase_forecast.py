"""Routes: seasonal purchase forecast (v87.12). Read only. Suggestions go to Purchase Drafts; nothing is ordered here."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import purchase_forecast as PF

FORECAST_ROLES = ('Admin', 'Pharmacist')


def _net_sold(cur, date_sql_from, date_sql_to):
    cur.execute(f"""SELECT m.medicine_id, m.name, m.stock_quantity, m.reorder_level,
                           IFNULL((SELECT SUM(si.quantity - IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                                                    WHERE ri.sale_item_id = si.sale_item_id), 0))
                                   FROM sale_items si JOIN sales s ON s.sale_id = si.sale_id
                                   WHERE si.medicine_id = m.medicine_id
                                     AND DATE(s.sale_date) BETWEEN {date_sql_from} AND {date_sql_to}), 0) AS sold
                    FROM medicines m WHERE m.is_deleted = 0""")
    return {r['medicine_id']: r for r in cur.fetchall()}


@app.route('/purchase/forecast')
@login_required
@role_required(*FORECAST_ROLES)
@guarded
def purchase_forecast():
    cur = mysql.connection.cursor()
    rows = []
    try:
        recent = _net_sold(cur, 'CURDATE() - INTERVAL 30 DAY', 'CURDATE()')
        last_year = _net_sold(cur, 'CURDATE() - INTERVAL 365 DAY', 'CURDATE() - INTERVAL 335 DAY')
        for mid, r in recent.items():
            ly = last_year.get(mid, {}).get('sold', 0)
            f = PF.forecast(r['sold'], ly, r['stock_quantity'], r['reorder_level'])
            if f['suggested'] > 0 or f['seasonal']:
                rows.append(dict(name=r['name'], stock=int(r['stock_quantity'] or 0), recent=int(r['sold'] or 0),
                                 last_year=int(ly or 0), **f))
    except Exception:
        app.logger.exception('purchase forecast failed')
        flash_unexpected('Could not build the forecast.')
    finally:
        cur.close()
    rows.sort(key=lambda x: (not x['seasonal'], -x['suggested'], x['name']))
    return render_template('purchase_forecast.html', rows=rows, cover=PF.COVER_DAYS,
                           shop=get_setting('shop_name'))
