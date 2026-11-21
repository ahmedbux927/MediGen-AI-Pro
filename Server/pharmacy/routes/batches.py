"""Routes: batches."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _as_date, _like, _stock_mismatches


@app.route('/batches')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def batches():
    q = request.args.get('q', '').strip()[:60]
    flt = request.args.get('filter', 'active')
    page = max(1, request.args.get('page', 1, type=int))
    per = 25

    where, params = [], []
    if q:
        where.append("(m.name LIKE %s OR b.batch_number LIKE %s)")
        params += [_like(q)] * 2
    conditions = {
        'active':  "(b.quantity > 0)",
        'expired': "(b.quantity > 0 AND b.expiry_date < CURDATE())",
        'soon':    "(b.quantity > 0 AND b.expiry_date >= CURDATE() AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY))",  # v88.00: E1 - days=30/60/90 narrows this below
        'ok':      "(b.quantity > 0 AND b.expiry_date > DATE_ADD(CURDATE(), INTERVAL 90 DAY))",
        'empty':   "(b.quantity <= 0)",
    }
    if flt in conditions:
        cond = conditions[flt]
        if flt == 'soon':   # v88.00: E1 - dashboard expiry buckets: ?filter=soon&days=30|60|90
            days = request.args.get('days', 90, type=int)
            if days in (30, 60, 90):
                cond = cond.replace('INTERVAL 90 DAY', f'INTERVAL {days} DAY')
        where.append(cond)
    else:
        flt = 'all'
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    joins = "FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id AND m.is_deleted = 0"

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS total " + joins + wsql, params)
    total = cur.fetchone()['total']
    pages = max(1, math.ceil(total / per))
    page = min(page, pages)
    offset = (page - 1) * per
    cur.execute("SELECT b.*, m.name AS medicine_name, DATEDIFF(b.expiry_date, CURDATE()) AS days_left, "
                + BATCH_STATUS_SQL + " AS status " + joins + wsql +
                " ORDER BY b.expiry_date ASC, b.batch_id ASC LIMIT %s OFFSET %s", params + [per, offset])
    rows = cur.fetchall()

    cur.execute("""SELECT SUM(quantity > 0) AS active_batches,
                          SUM(quantity > 0 AND expiry_date < CURDATE()) AS expired_batches,
                          SUM(CASE WHEN quantity > 0 AND expiry_date < CURDATE() THEN quantity ELSE 0 END) AS expired_units,
                          SUM(CASE WHEN quantity > 0 AND expiry_date < CURDATE()
                                   THEN quantity * IFNULL(purchase_price, 0) ELSE 0 END) AS expired_value,
                          SUM(quantity > 0 AND expiry_date >= CURDATE()
                              AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)) AS soon_batches
                   FROM batches""")
    s = cur.fetchone()
    stats = {k: (float(s[k] or 0) if k == 'expired_value' else int(s[k] or 0)) for k in
             ('active_batches', 'expired_batches', 'expired_units', 'expired_value', 'soon_batches')}
    cur.execute("""SELECT COUNT(*) AS n FROM (
                       SELECT m.medicine_id FROM medicines m LEFT JOIN batches b ON b.medicine_id = m.medicine_id
                       WHERE m.is_deleted = 0 GROUP BY m.medicine_id, m.stock_quantity
                       HAVING IFNULL(m.stock_quantity, 0) <> IFNULL(SUM(b.quantity), 0)) x""")
    mismatch = cur.fetchone()['n']
    cur.close()
    return render_template('batches.html', batches=rows, stats=stats, mismatch=mismatch, q=q, flt=flt,
                           page=page, pages=pages, total=total, offset=offset)

@app.route('/batches/writeoff/<int:bid>', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def writeoff_batch(bid):
    """Remove an EXPIRED batch from stock (and write it in the stock history)."""
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT b.batch_id, b.medicine_id, b.batch_number, b.expiry_date, b.quantity, m.name, m.stock_quantity
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE b.batch_id = %s FOR UPDATE""", (bid,))
        b = cur.fetchone()
        if not b or b['quantity'] <= 0:
            flash('Nothing to write off for this batch', 'warning')
            return redirect(url_for('batches'))
        if _as_date(b['expiry_date']) >= date.today():
            flash('Only expired batches can be written off', 'warning')
            return redirect(url_for('batches'))
        old = b['stock_quantity'] or 0
        new = max(0, old - b['quantity'])
        cur.execute("UPDATE batches SET quantity = 0 WHERE batch_id=%s", (bid,))
        cur.execute("UPDATE medicines SET stock_quantity=%s WHERE medicine_id=%s", (new, b['medicine_id']))
        cur.execute("""INSERT INTO stock_adjustments (medicine_id, user_id, change_qty, old_stock, new_stock, reason, note)
                       VALUES (%s,%s,%s,%s,%s,'Expired',%s)""",
                    (b['medicine_id'], session['user_id'], new - old, old, new, f"Write-off batch {b['batch_number']}"))
        audit(cur, 'batch.writeoff', 'batch', bid, f"{b['name']} {b['batch_number']}: {b['quantity']} units")
        mysql.connection.commit()
        flash(f"Expired batch {b['batch_number']} of {b['name']} removed ({b['quantity']} units)", 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('batches'))

@app.route('/batches/reconcile', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
@guarded
def reconcile_batches():
    """Make the batches add up to the stock of every medicine (stock_quantity is the truth)."""
    cur = mysql.connection.cursor()
    default_expiry = (date.today() + timedelta(days=365)).isoformat()
    if request.method == 'POST':
        try:
            exp = datetime.strptime(request.form.get('default_expiry', ''), '%Y-%m-%d').date()
            if exp <= date.today():
                raise ValueError
        except ValueError:
            cur.close()
            flash('Please enter a future expiry date for the units that have no batch', 'danger')
            return redirect(url_for('reconcile_batches'))
        added = trimmed = 0
        try:
            for r in _stock_mismatches(cur):
                if r['diff'] > 0:
                    batch_no = f"OPENING-{r['medicine_id']}"
                    cur.execute("SELECT batch_id FROM batches WHERE medicine_id=%s AND batch_number=%s FOR UPDATE",
                                (r['medicine_id'], batch_no))
                    ex = cur.fetchone()
                    if ex:
                        cur.execute("UPDATE batches SET quantity = quantity + %s WHERE batch_id=%s", (r['diff'], ex['batch_id']))
                    else:
                        cur.execute("""INSERT INTO batches (medicine_id, batch_number, expiry_date, quantity, purchase_price)
                                       VALUES (%s,%s,%s,%s,%s)""", (r['medicine_id'], batch_no, exp, r['diff'], r['cost']))
                    added += 1
                else:
                    remaining = -r['diff']
                    cur.execute("""SELECT batch_id, quantity FROM batches WHERE medicine_id=%s AND quantity > 0
                                   ORDER BY expiry_date ASC, batch_id ASC FOR UPDATE""", (r['medicine_id'],))
                    for b in cur.fetchall():
                        if remaining <= 0:
                            break
                        take = min(b['quantity'], remaining)
                        cur.execute("UPDATE batches SET quantity = quantity - %s WHERE batch_id=%s", (take, b['batch_id']))
                        remaining -= take
                    trimmed += 1
            audit(cur, 'batch.reconcile', None, None, f"{added} opening batch(es), {trimmed} trimmed")
            mysql.connection.commit()
            flash(f'Batches synced with stock: {added} medicine(s) got an opening batch, {trimmed} medicine(s) were trimmed.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash_unexpected('Something went wrong.')
        finally:
            cur.close()
        return redirect(url_for('batches'))
    items = _stock_mismatches(cur)
    cur.close()
    return render_template('batch_reconcile.html', items=items, default_expiry=default_expiry,
                           min_expiry=(date.today() + timedelta(days=1)).isoformat())
