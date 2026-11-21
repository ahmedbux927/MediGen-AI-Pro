"""Routes: sales."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _like, _num, _return_items, _valid_date
from pharmacy.services.sale_guard import sale_fingerprint   # B1 double-submit guard
from pharmacy.services import drip_record as DR
from pharmacy.services import interactions as IX   # v87.07
from pharmacy.services import product_sections as PS
from pharmacy.repos import cash_drawer as CDR
from pharmacy.services.cash_drawer import lock_message as cash_lock_message   # v87.03
from pharmacy.services.sales import read_lines, reserve_lines, calculate_bill, claim_guard, save_sale, check_scheduled   # B3 rules
from pharmacy.services import held_bills as HB   # Stage 4: hold / resume bills at the counter
import json as _json   # held-bill payloads on the Held Bills page


@app.route('/sales')
@login_required
@guarded
def sales():
    q = request.args.get('q', '').strip()[:60]
    flt = request.args.get('filter', 'all')
    d_from = _valid_date(request.args.get('from', ''))
    d_to = _valid_date(request.args.get('to', ''))
    page = max(1, request.args.get('page', 1, type=int))
    per = request.args.get('per', 15, type=int)
    if per not in (15, 50, 100):
        per = 15

    where, params = [], []
    if q:
        where.append("(c.name LIKE %s OR u.full_name LIKE %s OR s.sale_id = %s)")
        params += [_like(q), _like(q), int(q) if q.isdigit() else 0]
    if flt == 'due':
        where.append(f"({DUE_SQL} > 0.004)")
    elif flt == 'paid':
        where.append(f"({DUE_SQL} <= 0.004)")
    elif flt == 'returned':
        where.append("(s.returned_amount > 0)")
    else:
        flt = 'all'
    if d_from:
        where.append("(DATE(s.sale_date) >= %s)")
        params.append(d_from)
    if d_to:
        where.append("(DATE(s.sale_date) <= %s)")
        params.append(d_to)
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    joins = """FROM sales s
               LEFT JOIN customers c ON s.customer_id = c.customer_id
               LEFT JOIN users u ON s.user_id = u.user_id"""

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS total " + joins + wsql, params)
    total = cur.fetchone()['total']
    pages = max(1, math.ceil(total / per))
    page = min(page, pages)
    offset = (page - 1) * per
    cur.execute("SELECT s.*, c.name AS customer_name, u.full_name AS cashier, " + DUE_SQL + " AS due_amount " +
                joins + wsql + " ORDER BY s.sale_id DESC LIMIT %s OFFSET %s", params + [per, offset])
    rows = cur.fetchall()

    cur.execute("""SELECT COUNT(*) AS cnt, IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
                   FROM sales WHERE DATE(sale_date) = CURDATE()""")
    t = cur.fetchone()
    cur.execute("""SELECT IFNULL(SUM(total_amount - returned_amount - paid_amount), 0) AS dues,
                          SUM(total_amount - returned_amount - paid_amount > 0.004) AS due_count
                   FROM sales""")
    d = cur.fetchone()
    cur.close()
    stats = {'today_count': int(t['cnt']), 'today_revenue': float(t['revenue']),
             'dues': max(0.0, float(d['dues'])), 'due_count': int(d['due_count'] or 0)}
    qs = {'q': q, 'filter': flt, 'from': d_from, 'to': d_to, 'per': per}       # search settings kept in the page links
    return render_template('sales.html', sales=rows, stats=stats, q=q, flt=flt, d_from=d_from, d_to=d_to,
                           page=page, pages=pages, total=total, offset=offset, qs=qs)

@app.route('/sales/new', methods=['GET', 'POST'])
@login_required
@guarded
def new_sale():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        try:
            # v86.62 stage 2: offline bill id. Same id = same bill, saved once. Sync calls send the header X-Offline-Sync.
            offline_sync = bool(request.headers.get('X-Offline-Sync'))
            client_uuid = (request.form.get('client_uuid') or '').strip()[:64] or None
            if client_uuid:
                cur.execute("SELECT sale_id FROM sales WHERE client_uuid = %s", (client_uuid,))
                done = cur.fetchone()
                if done:
                    mysql.connection.rollback()
                    if offline_sync:
                        return jsonify(ok=True, sale_id=done['sale_id'], already_saved=True)
                    return redirect(url_for('invoice_thermal', sale_id=done['sale_id'], print=1))
            customer_id = request.form.get('customer_id') or None
            payment = request.form.get('payment_method', 'Cash')
            if payment not in PAY_METHODS:
                raise ValueError('Invalid payment method')
            rx_raw = (request.form.get('prescription_id') or '').strip()
            rx_id = int(rx_raw) if rx_raw.isdigit() else None
            if rx_id:
                cur.execute("SELECT prescription_id, customer_id FROM prescriptions WHERE prescription_id=%s", (rx_id,))
                rx = cur.fetchone()
                if not rx:
                    raise ValueError('Prescription not found')
                if customer_id is None:
                    customer_id = rx['customer_id']
                elif str(rx['customer_id']) != str(customer_id):
                    raise ValueError('This prescription belongs to another customer')

            wanted = read_lines(request.form.getlist('medicine_id[]'), request.form.getlist('quantity[]'))
            drip_routes = {}                                   # v85: route picked for drip/injection rows
            for mid_text, route_text in zip(request.form.getlist('medicine_id[]'), request.form.getlist('drip_route[]')):
                if mid_text.isdigit() and route_text in DR.ROUTES:
                    drip_routes[int(mid_text)] = route_text
            lines, subtotal, med_names = reserve_lines(cur, wanted, allow_short=offline_sync)   # v86.66: offline bills are never refused for stock
            if customer_id:
                cur.execute("SELECT medical_history FROM customers WHERE customer_id=%s", (customer_id,))
                hist = cur.fetchone()
                for w in allergy_warnings((hist or {}).get('medical_history'), med_names):
                    flash(w, 'warning')

            discount_text = request.form.get('discount')
            paid_text = request.form.get('paid_amount', '').strip()
            bill = calculate_bill(subtotal, _num(discount_text), request.form.get('discount_type') == 'percent',
                                  _num(paid_text) if paid_text else None, customer_id, session.get('role'),
                                  get_cashier_max() if session.get('role') == 'Cashier' else None,
                                  get_tax_rate())

            scheduled = check_scheduled(cur, lines, rx_id)   # Phase 4: prescription for scheduled medicines
            if not offline_sync:   # v87.03: live cash bills need an open drawer (offline bills are checked on arrival)
                lock = cash_lock_message(CDR.open_session(cur) is not None, payment, bill['paid'],
                                         'before taking cash for this bill')
                if lock:
                    mysql.connection.rollback()
                    flash(lock, 'danger')
                    return redirect(url_for('new_sale'))

            # B1: the same bill sent twice within a few seconds (double click) is saved once
            fingerprint = sale_fingerprint(session['user_id'], customer_id, payment, rx_id, wanted,
                                           discount_text, request.form.get('discount_type'), paid_text)
            if not claim_guard(cur, fingerprint, session['user_id']):
                mysql.connection.rollback()
                flash('This bill was just saved. Check the sales list before adding it again.', 'warning')
                return redirect(url_for('sales'))

            sale_id = save_sale(cur, session['user_id'], customer_id, payment, rx_id, subtotal, bill, lines,
                                get_tax_rate(), audit, scheduled=scheduled, drip_routes=drip_routes)
            total, paid = bill['total'], bill['paid']
            if client_uuid:
                cur.execute("UPDATE sales SET client_uuid = %s WHERE sale_id = %s", (client_uuid, sale_id))
            mysql.connection.commit()
            if offline_sync:
                session.pop('sale_cart', None)
                return jsonify(ok=True, sale_id=sale_id, total=total, paid=paid)
            session.pop('sale_cart', None)                # v86: cart is used up once the sale is saved
            msg = f'Sale #{sale_id} completed. Total: Rs. {total:,.2f}'
            if total - paid > 0.004:
                msg += f' | Balance (credit): Rs. {total - paid:,.2f}'
            flash(msg, 'success')
            try:                                           # v87.07: warnings only, the sale is already saved
                for w in IX.warnings_for_bill(cur, [mid for mid, _p, _parts in lines]):
                    flash(w, 'warning')
            except Exception:
                app.logger.exception('interaction check failed')
            # POS: open the 80 mm receipt and print it straight away (?print=1); the A4 invoice is still at /invoice/<id>
            return redirect(url_for('invoice_thermal', sale_id=sale_id, print=1))
        except ValueError as e:
            mysql.connection.rollback()
            msg = (str(e) if str(e) and not str(e).startswith(('invalid literal', 'could not convert'))
                   else 'Invalid number format!')
            if request.headers.get('X-Offline-Sync'):
                return jsonify(ok=False, error=msg), 400
            flash(msg, 'danger')
            return redirect(url_for('new_sale'))
        except Exception as e:
            mysql.connection.rollback()
            if request.headers.get('X-Offline-Sync'):
                flash_unexpected('Something went wrong.')
                return jsonify(ok=False, error='Server error. The bill stays in the queue.'), 500
            flash_unexpected('Something went wrong.')
            return redirect(url_for('new_sale'))
        finally:
            cur.close()

    prefill, prefill_customer, prefill_rx, prefill_names = [], None, None, []
    rx_names = {}                                         # v86.16: names for the out-of-stock warning
    resume = session.pop('resume_hold', None)             # Stage 4: a resumed held bill fills the form
    if resume:
        prefill = [{'mid': l['medicine_id'], 'qty': l['quantity']} for l in resume.get('lines', [])]
        prefill_customer = resume.get('customer_id')
        for p in prefill:
            cur.execute("SELECT name FROM medicines WHERE medicine_id=%s", (p['mid'],))
            row = cur.fetchone()
            if row:
                rx_names[p['mid']] = row['name']
        flash('Held bill resumed. Check the quantities, then complete the sale.', 'info')
    rx_get = request.args.get('rx', type=int)
    if rx_get:
        cur.execute("SELECT prescription_id, customer_id, doctor_name FROM prescriptions WHERE prescription_id=%s", (rx_get,))
        rx = cur.fetchone()
        if not rx:
            flash('Prescription not found', 'danger')
        else:
            prefill_rx, prefill_customer = rx['prescription_id'], rx['customer_id']
            cur.execute("SELECT COUNT(*) AS n FROM sales WHERE prescription_id=%s", (rx_get,))
            if cur.fetchone()['n']:
                flash(f'Prescription #{rx_get} was already dispensed before. Check the quantities.', 'warning')
            cur.execute("""SELECT pi.medicine_id, pi.dosage, m.name AS medicine_name, m.stock_quantity
                           FROM prescription_items pi JOIN medicines m ON pi.medicine_id = m.medicine_id
                           WHERE pi.prescription_id=%s ORDER BY pi.item_id""", (rx_get,))
            for it in cur.fetchall():
                prefill.append({'mid': it['medicine_id'], 'qty': 1})     # pharmacist sets the real quantity
                prefill_names.append(it['medicine_name'])
                rx_names[it['medicine_id']] = it['medicine_name']
            cur.execute("SELECT medical_history FROM customers WHERE customer_id=%s", (rx['customer_id'],))
            hist = cur.fetchone()
            for w in allergy_warnings((hist or {}).get('medical_history'), prefill_names):
                flash(w, 'warning')
    med_get = request.args.get('med', type=int)
    if med_get and not prefill_rx:
        qty_get = max(1, min(50, request.args.get('qty', 1, type=int) or 1))
        prefill = [{'mid': med_get, 'qty': qty_get}]
        prefill_customer = request.args.get('customer', type=int)
    if not prefill_rx:                                    # v86: items collected from the product sections
        seen_ids = {p['mid'] for p in prefill}
        for item in session.get('sale_cart') or []:
            if item['mid'] not in seen_ids:
                prefill.append({'mid': item['mid'], 'qty': item['qty']})
                seen_ids.add(item['mid'])
    cur.execute("""SELECT m.medicine_id, m.name, m.barcode, m.price, m.stock_quantity, m.dosage_form, m.units_per_pack,
                          IFNULL((SELECT SUM(b.quantity) FROM batches b
                                  WHERE b.medicine_id = m.medicine_id AND b.quantity > 0 AND b.expiry_date >= CURDATE()), 0) AS fresh_qty,
                          (SELECT COUNT(*) FROM batches b2 WHERE b2.medicine_id = m.medicine_id) AS batch_count
                   FROM medicines m WHERE m.stock_quantity > 0 AND m.is_deleted = 0 ORDER BY m.name""")
    meds = []
    for m in cur.fetchall():
        m['available'] = min(int(m['stock_quantity']), int(m['fresh_qty'])) if m['batch_count'] else int(m['stock_quantity'])
        m['is_drip'] = DR.is_drip_form(m.get('dosage_form'))
        m['section'] = PS.section_for(m.get('dosage_form'))
        if m['available'] > 0:
            meds.append(m)
    cur.execute("""SELECT c.customer_id, c.name,
                          IFNULL((SELECT SUM(s.total_amount - s.returned_amount - s.paid_amount)
                                  FROM sales s WHERE s.customer_id = c.customer_id), 0) AS due
                   FROM customers c ORDER BY c.name""")
    custs = cur.fetchall()
    # v91.00: the sale page warns up-front when the cash drawer is closed,
    # instead of refusing the bill only after submit (looked like "no invoice").
    drawer_open = CDR.open_session(cur) is not None
    cur.close()
    avail = {m['medicine_id'] for m in meds}
    left = [p for p in prefill if p['mid'] not in avail]
    if left:
        names = [rx_names.get(p['mid'], '#%s' % p['mid']) for p in left]
        flash('These medicines are out of stock and were not added: ' + ', '.join(names) + '.', 'warning')
    prefill = [p for p in prefill if p['mid'] in avail]
    return render_template('new_sale.html', medicines=meds, customers=custs, tax_rate=get_tax_rate(),
                           cashier_max=get_cashier_max(), prefill=prefill, drawer_open=drawer_open,
                           prefill_customer=prefill_customer, prefill_rx=prefill_rx, drip_routes=DR.ROUTES,
                           sections=PS.SECTIONS)

@app.route('/sales/hold', methods=['POST'])
@login_required
@guarded
def hold_sale():
    """Stage 4: park the current bill and clear the counter for the next customer.
    Stock is NOT reserved; the normal stock check runs when the resumed bill is completed."""
    cur = mysql.connection.cursor()
    try:
        wanted = read_lines(request.form.getlist('medicine_id[]'), request.form.getlist('quantity[]'))
        customer_id = request.form.get('customer_id') or None
        hold_id = HB.hold_bill(cur, session['user_id'], 1, customer_id, wanted,
                               (request.form.get('hold_note') or '').strip())
        mysql.connection.commit()
        flash(f'Bill held (#{hold_id}). Resume it any time from Held Bills.', 'success')
    except (HB.HoldError, ValueError) as e:   # BillError is a ValueError
        mysql.connection.rollback()
        flash(str(e) if str(e) else 'Could not hold this bill.', 'danger')
    finally:
        cur.close()
    return redirect(url_for('new_sale'))


@app.route('/sales/held')
@login_required
@guarded
def held_bills_page():
    cur = mysql.connection.cursor()
    HB.expire_old_holds(cur)
    mysql.connection.commit()
    cur.execute("""SELECT h.hold_id, h.counter_no, h.customer_id, h.payload, h.created_at,
                          u.username, c.name AS customer_name
                   FROM held_bills h LEFT JOIN users u ON u.user_id = h.user_id
                   LEFT JOIN customers c ON c.customer_id = h.customer_id
                   WHERE h.status='open' ORDER BY h.hold_id""")
    holds = []
    for h in cur.fetchall():
        payload = _json.loads(h['payload'])
        lines = []
        for l in payload.get('lines', []):
            cur.execute("SELECT name FROM medicines WHERE medicine_id=%s", (l['medicine_id'],))
            m = cur.fetchone()
            lines.append({'name': (m or {}).get('name', '#%s' % l['medicine_id']), 'qty': l['quantity']})
        holds.append({**h, 'lines': lines, 'note': payload.get('note', '')})
    cur.close()
    return render_template('held_bills.html', holds=holds)


@app.route('/sales/held/<int:hold_id>/resume', methods=['POST'])
@login_required
@guarded
def resume_held_bill(hold_id):
    cur = mysql.connection.cursor()
    try:
        session['resume_hold'] = HB.resume_hold(cur, hold_id)
        mysql.connection.commit()
    except HB.HoldError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('held_bills_page'))
    finally:
        cur.close()
    return redirect(url_for('new_sale'))


@app.route('/sales/held/<int:hold_id>/discard', methods=['POST'])
@login_required
@guarded
def discard_held_bill(hold_id):
    cur = mysql.connection.cursor()
    try:
        HB.discard_hold(cur, hold_id)
        mysql.connection.commit()
        flash('Held bill discarded.', 'success')
    except HB.HoldError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    finally:
        cur.close()
    return redirect(url_for('held_bills_page'))


@app.route('/sales/<int:sale_id>/pay', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def receive_payment(sale_id):
    """Customer pays (part of) an unpaid balance."""
    method = request.form.get('method', 'Cash')
    try:
        amount = round(float(request.form.get('amount', '0')), 2)
        if not math.isfinite(amount):
            amount = 0
    except ValueError:
        amount = 0
    if method not in PAY_METHODS or amount <= 0:
        flash('Please enter a valid amount and payment method', 'danger')
        return redirect(request.referrer or url_for('sales'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT total_amount, returned_amount, paid_amount FROM sales WHERE sale_id=%s FOR UPDATE", (sale_id,))
        s = cur.fetchone()
        if not s:
            flash('Sale not found', 'danger')
            return redirect(url_for('sales'))
        due = round(float(s['total_amount']) - float(s['returned_amount']) - float(s['paid_amount']), 2)
        if amount > due + 0.004:
            mysql.connection.rollback()
            flash(f'Amount is more than the balance (Rs. {max(due, 0):,.2f})', 'danger')
            return redirect(request.referrer or url_for('sales'))
        lock = cash_lock_message(CDR.open_session(cur) is not None, method, amount, 'before taking this cash payment')
        if lock:                                  # v87.03
            mysql.connection.rollback()
            flash(lock, 'danger')
            return redirect(request.referrer or url_for('sales'))
        cur.execute("UPDATE sales SET paid_amount = paid_amount + %s WHERE sale_id=%s", (amount, sale_id))
        cur.execute("INSERT INTO sale_payments (sale_id, user_id, amount, method) VALUES (%s,%s,%s,%s)",
                    (sale_id, session['user_id'], amount, method))
        audit(cur, 'payment.receive', 'sale', sale_id, f"Rs. {amount:.2f} by {method}")
        mysql.connection.commit()
        left = max(0.0, due - amount)
        flash(f'Payment of Rs. {amount:,.2f} received for sale #{sale_id}.' +
              (f' Remaining balance: Rs. {left:,.2f}' if left > 0.004 else ' Balance cleared.'), 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(request.referrer or url_for('sales'))

@app.route('/sales/<int:sale_id>/return', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def sale_return(sale_id):
    """Customer brings medicines back: stock goes up, refund / balance is adjusted."""
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT s.*, c.name AS customer_name FROM sales s LEFT JOIN customers c ON s.customer_id = c.customer_id
                       WHERE s.sale_id=%s""" + (" FOR UPDATE" if request.method == 'POST' else ""), (sale_id,))
        sale = cur.fetchone()
        if not sale:
            flash('Sale not found', 'danger')
            return redirect(url_for('sales'))
        subtotal = float(sale['subtotal_amount'] or 0)
        ratio = float(sale['total_amount']) / subtotal if subtotal > 0 else 1.0    # discount + tax share
        items = _return_items(cur, sale_id, ratio)

        if request.method == 'POST':
            reason = request.form.get('reason', '').strip()[:255]
            picked = []
            for it in items:
                raw = (request.form.get(f"ret_{it['sale_item_id']}") or '0').strip() or '0'
                q = int(raw)
                if q < 0 or q > it['returnable']:
                    raise ValueError(f"You can return at most {it['returnable']} of {it['name']}")
                if q > 0:
                    picked.append((it, q))
            if not picked:
                flash('Please enter the quantity of at least one item to return', 'warning')
                return redirect(url_for('sale_return', sale_id=sale_id))

            refund = 0.0
            cur.execute("INSERT INTO sale_returns (sale_id, user_id, refund_amount, reason) VALUES (%s,%s,0,%s)",
                        (sale_id, session['user_id'], reason or None))
            return_id = cur.lastrowid
            for it, q in picked:
                amount = round(q * it['unit_refund'], 2)
                refund += amount
                cur.execute("""INSERT INTO sale_return_items (return_id, sale_item_id, medicine_id, batch_id, quantity, amount)
                               VALUES (%s,%s,%s,%s,%s,%s)""", (return_id, it['sale_item_id'], it['medicine_id'], it['batch_id'], q, amount))
                cur.execute("UPDATE medicines SET stock_quantity = stock_quantity + %s WHERE medicine_id=%s", (q, it['medicine_id']))
                if it['batch_id']:
                    cur.execute("UPDATE batches SET quantity = quantity + %s WHERE batch_id=%s", (q, it['batch_id']))
                cur.execute("SELECT stock_quantity FROM medicines WHERE medicine_id=%s", (it['medicine_id'],))
                new_stock = cur.fetchone()['stock_quantity']
                cur.execute("""INSERT INTO stock_adjustments (medicine_id, user_id, change_qty, old_stock, new_stock, reason, note)
                               VALUES (%s,%s,%s,%s,%s,'Customer return',%s)""",
                            (it['medicine_id'], session['user_id'], q, new_stock - q, new_stock, f'Return of sale #{sale_id}'))
            refund = round(refund, 2)
            total, paid = float(sale['total_amount']), float(sale['paid_amount'])
            new_returned = min(total, round(float(sale['returned_amount']) + refund, 2))
            cash_back = round(max(0.0, paid - (total - new_returned)), 2)     # only money the customer really paid is given back
            cur.execute("UPDATE sales SET returned_amount=%s, paid_amount=%s WHERE sale_id=%s",
                        (new_returned, round(paid - cash_back, 2), sale_id))
            cur.execute("UPDATE sale_returns SET refund_amount=%s WHERE return_id=%s", (refund, return_id))
            audit(cur, 'sale.return', 'sale', sale_id, f"Refund {refund:.2f}, reason: {reason or '-'}")
            mysql.connection.commit()
            msg = f'Return saved. Value of returned medicines: Rs. {refund:,.2f}.'
            if cash_back > 0:
                msg += f' Give Rs. {cash_back:,.2f} back to the customer.'
            if refund - cash_back > 0.004:
                msg += f' Rs. {refund - cash_back:,.2f} was taken off the customer balance.'
            flash(msg, 'success')
            return redirect(url_for('invoice', sale_id=sale_id))
        return render_template('returns.html', sale=sale, items=items)
    except ValueError as e:
        mysql.connection.rollback()
        flash(str(e) if str(e) and not str(e).startswith('invalid literal') else 'Invalid number format!', 'danger')
        return redirect(url_for('sale_return', sale_id=sale_id))
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
        return redirect(url_for('sales'))
    finally:
        cur.close()

@app.route('/invoice/<int:sale_id>')
@login_required
@guarded
def invoice(sale_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.*, c.name AS customer_name, c.contact_number, c.email,
               c.medical_history, u.full_name AS cashier,
               (s.total_amount - s.returned_amount - s.paid_amount) AS due_amount
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.sale_id = %s
    """, (sale_id,))
    sale = cur.fetchone()
    if not sale:
        cur.close()
        flash('Invoice not found', 'danger')
        return redirect(url_for('sales'))
    cur.execute("""
        SELECT m.name AS medicine_name, SUM(si.quantity) AS quantity, MAX(si.unit_price) AS unit_price,
               SUM(si.subtotal) AS subtotal
        FROM sale_items si
        JOIN medicines m ON si.medicine_id = m.medicine_id
        WHERE si.sale_id = %s
        GROUP BY si.medicine_id, m.name
        ORDER BY MIN(si.sale_item_id)
    """, (sale_id,))
    items = cur.fetchall()
    cur.execute("SELECT amount, method, created_at FROM sale_payments WHERE sale_id=%s ORDER BY payment_id", (sale_id,))
    payments = cur.fetchall()
    cur.close()
    return render_template('invoice.html', sale=sale, items=items, payments=payments)

# ---------- THERMAL (80 mm) RECEIPT ----------
@app.route('/invoice/<int:sale_id>/thermal')
@login_required
@guarded
def invoice_thermal(sale_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT s.*, c.name AS customer_name, u.full_name AS cashier
                       FROM sales s LEFT JOIN customers c ON s.customer_id = c.customer_id
                       LEFT JOIN users u ON s.user_id = u.user_id WHERE s.sale_id = %s""", (sale_id,))
        sale = cur.fetchone()
        if not sale:
            flash('Invoice not found', 'danger')
            return redirect(url_for('sales'))
        cur.execute("""SELECT m.name AS medicine_name, m.dosage_form, SUM(si.quantity) AS quantity, MAX(si.unit_price) AS unit_price,
                              SUM(si.subtotal) AS subtotal
                       FROM sale_items si JOIN medicines m ON si.medicine_id = m.medicine_id
                       WHERE si.sale_id = %s GROUP BY si.medicine_id, m.name, m.dosage_form ORDER BY MIN(si.sale_item_id)""", (sale_id,))
        items = cur.fetchall()
    except Exception as e:
        app.logger.exception('thermal receipt failed')
        flash_unexpected('Could not open receipt.')
        return redirect(url_for('sales'))
    finally:
        cur.close()
    # group the lines by product section, with a subtotal per section (medicines, syrups, creams, drip, others)
    labels = {k: lab for k, lab, ic, desc in PS.SECTIONS}
    groups = {}
    for it in items:
        key = PS.section_for(it.get('dosage_form'))
        g = groups.setdefault(key, {'label': labels[key], 'lines': [], 'subtotal': 0, 'units': 0})
        g['lines'].append(it)
        g['subtotal'] += float(it['subtotal'] or 0)
        g['units'] += int(it['quantity'] or 0)
    ordered = [groups[k] for k in PS.SECTION_KEYS if k in groups]
    return render_template('receipt_thermal.html', sale=sale, items=items, groups=ordered,
                           units=sum(g['units'] for g in ordered), shop=inject_shop()['shop'])
