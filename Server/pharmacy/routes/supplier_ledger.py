"""Routes: Supplier Summary (v86.47) and payments to suppliers (v86.48). Purchase amounts come from received orders."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _valid_date
from pharmacy.repos import supplier_ledger as repo


@app.route('/supplier-summary')
@login_required
@role_required('Admin')
@guarded
def supplier_summary():
    cur = mysql.connection.cursor()
    rows = repo.supplier_totals(cur)
    returns = repo.returns_by_supplier(cur)
    paid = repo.paid_by_supplier(cur)
    payments = repo.recent_payments(cur)
    cur.close()
    total_bought = total_returned = total_paid = 0.0
    for r in rows:
        r['bought'] = float(r['bought'] or 0)
        r['returned'] = returns.get(r['supplier_id'], 0.0)
        r['net'] = r['bought'] - r['returned']
        r['paid'] = paid.get(r['supplier_id'], 0.0)
        r['owed'] = r['net'] - r['paid']
        total_bought += r['bought']
        total_returned += r['returned']
        total_paid += r['paid']
    return render_template('supplier_summary.html', rows=rows, payments=payments, total_bought=total_bought,
                           total_returned=total_returned, total_net=total_bought - total_returned,
                           total_paid=total_paid, total_owed=total_bought - total_returned - total_paid,
                           today=date.today().isoformat(), shop=get_setting('shop_name'))


@app.route('/supplier-summary/payment', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def supplier_payment():
    """Record money paid to a supplier. Only records a payment; it does not change stock or purchases."""
    supplier_id = request.form.get('supplier_id', type=int)
    try:
        amount = round(float(request.form.get('amount', '').strip()), 2)
    except ValueError:
        amount = 0.0
    paid_on = _valid_date(request.form.get('paid_on', '').strip())
    method = (request.form.get('method') or 'Cash').strip()[:20]
    note = (request.form.get('note') or '').strip()[:255] or None
    if not supplier_id or amount <= 0 or not paid_on:
        flash('Supplier, amount (more than 0) and date are needed.', 'warning')
        return redirect(url_for('supplier_summary'))
    if paid_on > date.today().isoformat():
        flash('Payment date cannot be in the future.', 'warning')
        return redirect(url_for('supplier_summary'))
    cur = mysql.connection.cursor()
    try:
        if not repo.supplier_exists(cur, supplier_id):
            flash('Supplier not found.', 'danger')
            return redirect(url_for('supplier_summary'))
        pid = repo.insert_payment(cur, supplier_id, amount, paid_on, method, note, session.get('user_id'))
        audit(cur, 'supplier.payment', 'supplier', supplier_id, f'Paid Rs. {amount:.2f} ({method}) on {paid_on}',
              after={'payment_id': pid, 'amount': amount})
        mysql.connection.commit()
        flash(f'Payment of Rs. {amount:.2f} recorded.', 'success')
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
    return redirect(url_for('supplier_summary'))
