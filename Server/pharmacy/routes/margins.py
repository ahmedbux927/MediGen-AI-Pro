"""Routes: profit margin per item (v87.04). Read only."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _like
from pharmacy.services import margins as MG

MARGIN_ROLES = ('Admin', 'Pharmacist')
FILTERS = ('all',) + MG.STATUS_ORDER


@app.route('/margins')
@login_required
@role_required(*MARGIN_ROLES)
@guarded
def margins():
    f = request.args.get('f', 'all')
    if f not in FILTERS:
        f = 'all'
    q = (request.args.get('q') or '').strip()[:60]
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT m.medicine_id, m.name, m.barcode, m.dosage_form, m.price, m.cost_price,
                              lb.purchase_price AS batch_cost
                       FROM medicines m
                       LEFT JOIN (SELECT b.medicine_id, b.purchase_price
                                  FROM batches b
                                  JOIN (SELECT medicine_id, MAX(batch_id) AS last_id FROM batches GROUP BY medicine_id) x
                                    ON x.last_id = b.batch_id) lb ON lb.medicine_id = m.medicine_id
                       WHERE m.is_deleted = 0 ORDER BY m.name ASC""")
        raw = cur.fetchall()
    except Exception:
        app.logger.exception('margin report failed')
        raw = []
        flash_unexpected('Could not load the margin report.')
    finally:
        cur.close()
    rows = []
    for r in raw:
        cost, source = MG.pick_cost(r['batch_cost'], r['cost_price'])
        res = MG.compute(r['price'], cost)
        row = dict(medicine_id=r['medicine_id'], name=r['name'], barcode=r['barcode'], dosage_form=r['dosage_form'],
                   price=_num_or_none(r['price']), cost=cost, cost_source=source, **res)
        if q and q.lower() not in (r['name'] or '').lower() and q.lower() not in (r['barcode'] or '').lower():
            continue
        rows.append(row)
    summary = MG.counts(rows)
    rows.sort(key=MG.sort_key)
    shown = rows if f == 'all' else [r for r in rows if r['status'] == f]
    return render_template('margins.html', rows=shown, summary=summary, total=len(rows), f=f, q=q,
                           low_pct=MG.LOW_MARGIN_PCT, shop=get_setting('shop_name'))


def _num_or_none(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
