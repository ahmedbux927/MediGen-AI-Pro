"""Routes: supplier returns (expired / damaged / recalled stock sent back) and the alerts page (Sprint 1)."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _as_date, _stock_rows

RETURN_REASONS = ['Expired', 'Damaged', 'Recalled', 'Other']


@app.route('/alerts')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def alerts():
    """One page for what needs attention: low stock, expiring in 90 days, already expired."""
    cur = mysql.connection.cursor()
    try:
        low = _stock_rows(cur)
        cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity,
                              DATEDIFF(b.expiry_date, CURDATE()) AS days_left
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE b.quantity > 0 AND b.expiry_date >= CURDATE()
                         AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)
                       ORDER BY b.expiry_date ASC LIMIT 300""")
        expiring = cur.fetchall()
        cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity,
                              DATEDIFF(b.expiry_date, CURDATE()) AS days_left
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE b.quantity > 0 AND b.expiry_date < CURDATE()
                       ORDER BY b.expiry_date ASC LIMIT 300""")
        expired = cur.fetchall()
    finally:
        cur.close()
    return render_template('alerts.html', low=low, expiring=expiring, expired=expired)


@app.route('/supplier-returns')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def supplier_returns():
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT b.batch_id, b.batch_number, b.expiry_date, b.quantity, m.name AS medicine_name
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE b.quantity > 0 ORDER BY m.name ASC, b.expiry_date ASC LIMIT 500""")
        batches_list = cur.fetchall()
        cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name ASC")
        suppliers_list = cur.fetchall()
        cur.execute("""SELECT r.return_id, r.return_date, r.batch_number, r.quantity, r.unit_cost, r.reason, r.note,
                              m.name AS medicine_name, s.name AS supplier_name
                       FROM supplier_returns r
                       JOIN medicines m ON r.medicine_id = m.medicine_id
                       LEFT JOIN suppliers s ON r.supplier_id = s.supplier_id
                       ORDER BY r.return_id DESC LIMIT 100""")
        history = cur.fetchall()
    finally:
        cur.close()
    return render_template('supplier_returns.html', batches=batches_list, suppliers=suppliers_list,
                           history=history, reasons=RETURN_REASONS)


@app.route('/supplier-returns/new', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def record_supplier_return():
    """Record a return to the supplier: removes the units from the batch and the stock, and writes the history."""
    batch_id = request.form.get('batch_id', type=int)
    qty = request.form.get('quantity', type=int)
    reason = request.form.get('reason', '')
    note = request.form.get('note', '').strip()[:255] or None
    supplier_id = request.form.get('supplier_id', type=int) or None
    if reason not in RETURN_REASONS:
        reason = 'Other'
    if not batch_id or not qty or qty <= 0:
        flash('Please choose a batch and a quantity above 0', 'danger')
        return redirect(url_for('supplier_returns'))

    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT b.batch_id, b.medicine_id, b.batch_number, b.quantity, b.purchase_price,
                              m.name, m.stock_quantity, m.cost_price
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE b.batch_id = %s FOR UPDATE""", (batch_id,))
        b = cur.fetchone()
        if not b:
            flash('Batch not found', 'danger')
            return redirect(url_for('supplier_returns'))
        if qty > b['quantity']:
            flash(f"Only {b['quantity']} units are in this batch", 'danger')
            return redirect(url_for('supplier_returns'))
        if supplier_id:
            cur.execute("SELECT supplier_id FROM suppliers WHERE supplier_id = %s", (supplier_id,))
            if not cur.fetchone():
                flash('Supplier not found', 'danger')
                return redirect(url_for('supplier_returns'))

        old = int(b['stock_quantity'] or 0)
        new = max(0, old - qty)
        unit_cost = b['purchase_price'] or b['cost_price'] or 0
        cur.execute("UPDATE batches SET quantity = quantity - %s WHERE batch_id = %s", (qty, batch_id))
        cur.execute("UPDATE medicines SET stock_quantity = %s WHERE medicine_id = %s", (new, b['medicine_id']))
        cur.execute("""INSERT INTO stock_adjustments (medicine_id, user_id, change_qty, old_stock, new_stock, reason, note)
                       VALUES (%s,%s,%s,%s,%s,'Supplier return',%s)""",
                    (b['medicine_id'], session['user_id'], new - old, old, new,
                     f"Returned to supplier: batch {b['batch_number']} ({reason})"))
        cur.execute("""INSERT INTO supplier_returns (supplier_id, medicine_id, batch_id, batch_number, quantity,
                                                     unit_cost, reason, note, return_date, user_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,CURDATE(),%s)""",
                    (supplier_id, b['medicine_id'], batch_id, b['batch_number'], qty, unit_cost, reason, note,
                     session['user_id']))
        audit(cur, 'supplier_return.create', 'batch', batch_id, f"{b['name']} {b['batch_number']}: {qty} units ({reason})")
        mysql.connection.commit()
        flash(f"Returned {qty} units of {b['name']} (batch {b['batch_number']}) to the supplier", 'success')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('supplier_returns'))
