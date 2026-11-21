"""Routes: purchase."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _as_date, _read_purchase_rows


@app.route('/purchase')
@login_required
@role_required('Admin')
@guarded
def purchase():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT po.*, s.name AS supplier_name
                   FROM purchase_orders po
                   JOIN suppliers s ON po.supplier_id = s.supplier_id
                   ORDER BY po.po_id DESC""")
    data = cur.fetchall()
    cur.close()
    return render_template('purchase.html', purchases=data)

@app.route('/purchase/<int:po_id>/items')
@login_required
@role_required('Admin')
@guarded
def purchase_items_json(po_id):
    cur = mysql.connection.cursor()
    cur.execute("""SELECT m.name, pi.batch_number, pi.expiry_date, pi.quantity, pi.unit_price
                   FROM purchase_items pi JOIN medicines m ON pi.medicine_id = m.medicine_id
                   WHERE pi.po_id = %s ORDER BY pi.po_item_id""", (po_id,))
    rows = cur.fetchall()
    cur.close()
    return jsonify([{'name': r['name'], 'batch': r['batch_number'] or '-', 'expiry': str(r['expiry_date'] or '-'),
                     'qty': r['quantity'], 'price': str(r['unit_price'] or 0),
                     'line': str((r['unit_price'] or 0) * r['quantity'])} for r in rows])

@app.route('/purchase/new', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
@guarded
def new_purchase():
    today = date.today()
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id')
        rows, err = _read_purchase_rows(request.form, today)
        if not err and not supplier_id:
            err = 'Please choose a supplier'
        if err:
            cur.close()
            flash(err, 'danger')
            return redirect(url_for('new_purchase'))
        try:
            cur.execute("""INSERT INTO purchase_orders (supplier_id, order_date, delivery_date, status)
                           VALUES (%s, CURDATE(), CURDATE(), 'Received')""", (supplier_id,))
            po_id = cur.lastrowid
            total = 0
            for r in rows:
                batch_no = r['batch'] or f"B{po_id}-{r['mid']}"
                # the database trigger adds the quantity to medicines.stock_quantity
                cur.execute("""INSERT INTO purchase_items (po_id, medicine_id, batch_number, expiry_date, quantity, unit_price)
                               VALUES (%s,%s,%s,%s,%s,%s)""",
                            (po_id, r['mid'], batch_no, r['expiry'], r['qty'], r['price']))
                # keep the batches table in step
                cur.execute("""SELECT batch_id, expiry_date FROM batches
                               WHERE medicine_id=%s AND batch_number=%s FOR UPDATE""", (r['mid'], batch_no))
                b = cur.fetchone()
                if b:
                    if _as_date(b['expiry_date']) != r['expiry']:
                        raise BatchConflict(f"Batch {batch_no} already exists with expiry {b['expiry_date']}. "
                                            "Use a different batch number or the same expiry date.")
                    cur.execute("UPDATE batches SET quantity = quantity + %s, purchase_price = %s WHERE batch_id=%s",
                                (r['qty'], r['price'], b['batch_id']))
                else:
                    cur.execute("""INSERT INTO batches (medicine_id, batch_number, expiry_date, quantity, purchase_price)
                                   VALUES (%s,%s,%s,%s,%s)""",
                                (r['mid'], batch_no, r['expiry'], r['qty'], r['price']))
                cur.execute("UPDATE medicines SET cost_price=%s WHERE medicine_id=%s", (r['price'], r['mid']))
                total += r['qty'] * r['price']
            cur.execute("UPDATE purchase_orders SET total_amount=%s WHERE po_id=%s", (total, po_id))
            audit(cur, 'purchase.create', 'purchase', po_id, f"Total {total:.2f}")
            mysql.connection.commit()
            flash(f'Purchase #{po_id} saved. Stock and batches updated.', 'success')
            return redirect(url_for('purchase'))
        except BatchConflict as e:
            mysql.connection.rollback()
            flash(str(e), 'danger')
            return redirect(url_for('new_purchase'))
        except Exception as e:
            mysql.connection.rollback()
            flash_unexpected('Something went wrong.')
            return redirect(url_for('new_purchase'))
        finally:
            cur.close()
    cur.execute("SELECT * FROM suppliers ORDER BY name")
    sups = cur.fetchall()
    cur.execute("SELECT medicine_id, name FROM medicines WHERE is_deleted = 0 ORDER BY name")
    meds = cur.fetchall()
    cur.close()
    return render_template('new_purchase.html', suppliers=sups, medicines=meds,
                           min_expiry=(today + timedelta(days=1)).isoformat())
