"""Routes: prescriptions."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _clean_doctor, _customer_or_error, _like, _read_prescription_form, _save_items


@app.route('/prescriptions')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def prescriptions():
    q = request.args.get('q', '').strip()[:60]
    flt = request.args.get('filter', 'all')
    page = max(1, request.args.get('page', 1, type=int))
    per = 20
    disp = "(SELECT COUNT(*) FROM sales s WHERE s.prescription_id = p.prescription_id)"
    where, params = [], []
    if q:
        where.append("(c.name LIKE %s OR p.doctor_name LIKE %s OR p.prescription_id = %s)")
        params += [_like(q), _like(q), int(q) if q.isdigit() else 0]
    if flt == 'open':
        where.append(f"{disp} = 0")
    elif flt == 'dispensed':
        where.append(f"{disp} > 0")
    else:
        flt = 'all'
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    joins = "FROM prescriptions p JOIN customers c ON p.customer_id = c.customer_id"

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS total " + joins + wsql, params)
    total = cur.fetchone()['total']
    pages = max(1, math.ceil(total / per))
    page = min(page, pages)
    offset = (page - 1) * per
    cur.execute("""SELECT p.*, c.name AS customer_name,
                          (SELECT COUNT(*) FROM prescription_items pi WHERE pi.prescription_id = p.prescription_id) AS item_count,
                          """ + disp + """ AS dispensed_count,
                          (SELECT MAX(s.sale_id) FROM sales s WHERE s.prescription_id = p.prescription_id) AS sale_id
                   """ + joins + wsql + " ORDER BY p.prescription_id DESC LIMIT %s OFFSET %s", params + [per, offset])
    rows = cur.fetchall()
    cur.execute("""SELECT COUNT(*) AS total,
                          SUM((SELECT COUNT(*) FROM sales s WHERE s.prescription_id = p.prescription_id) > 0) AS dispensed
                   FROM prescriptions p""")
    s = cur.fetchone()
    cur.close()
    stats = {'total': int(s['total'] or 0), 'dispensed': int(s['dispensed'] or 0)}
    stats['open'] = stats['total'] - stats['dispensed']
    qs = {'q': q, 'filter': flt}
    return render_template('prescriptions.html', prescriptions=rows, stats=stats, q=q, flt=flt,
                           page=page, pages=pages, total=total, offset=offset, qs=qs)

@app.route('/prescriptions/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def add_prescription():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        try:
            cust = _customer_or_error(cur, request.form.get('customer_id'))
            doctor, notes, items, names = _read_prescription_form(cur, request.form)
            cur.execute("INSERT INTO prescriptions (customer_id, doctor_name, date_issued, notes) VALUES (%s,%s,CURDATE(),%s)",
                        (cust['customer_id'], doctor, notes))
            pid = cur.lastrowid
            _save_items(cur, pid, items)
            audit(cur, 'prescription.add', 'prescription', pid, f"{doctor}, {len(items)} medicine(s)")
            mysql.connection.commit()
            for w in allergy_warnings(cust['medical_history'], names):
                flash(w, 'warning')
            flash(f'Prescription #{pid} saved.', 'success')
            return redirect(url_for('prescriptions'))
        except ValueError as e:
            mysql.connection.rollback()
            flash(str(e), 'danger')
            return redirect(url_for('add_prescription'))
        except Exception as e:
            mysql.connection.rollback()
            flash_unexpected('Something went wrong.')
            return redirect(url_for('add_prescription'))
        finally:
            cur.close()
    cur.execute("SELECT customer_id, name, medical_history FROM customers ORDER BY name")
    custs = cur.fetchall()
    cur.execute("SELECT medicine_id, name FROM medicines WHERE is_deleted = 0 ORDER BY name")
    meds = cur.fetchall()
    cur.close()
    return render_template('add_prescription.html', customers=custs, medicines=meds)

@app.route('/prescriptions/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def edit_prescription(pid):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT p.*, c.name AS customer_name, c.medical_history
                       FROM prescriptions p JOIN customers c ON p.customer_id = c.customer_id
                       WHERE p.prescription_id = %s""", (pid,))
        rx = cur.fetchone()
        if not rx:
            flash('Prescription not found', 'danger')
            return redirect(url_for('prescriptions'))
        cur.execute("SELECT sale_id FROM sales WHERE prescription_id=%s ORDER BY sale_id", (pid,))
        sale_ids = [r['sale_id'] for r in cur.fetchall()]
        dispensed = bool(sale_ids)

        if request.method == 'POST':
            doctor, notes, items, names = _read_prescription_form(cur, request.form)
            cur.execute("""SELECT m.name, pi.dosage, pi.duration_days FROM prescription_items pi
                           JOIN medicines m ON pi.medicine_id = m.medicine_id WHERE pi.prescription_id=%s ORDER BY pi.item_id""", (pid,))
            old_items = cur.fetchall()
            old_snapshot = {'doctor': rx['doctor_name'], 'notes': rx['notes'], 'medicines': old_items}
            cur.execute("UPDATE prescriptions SET doctor_name=%s, notes=%s WHERE prescription_id=%s", (doctor, notes, pid))
            cur.execute("DELETE FROM prescription_items WHERE prescription_id=%s", (pid,))
            _save_items(cur, pid, items)
            note = f"{doctor}, {len(items)} medicine(s)"
            if dispensed:
                note += f" (sale {', '.join('#%d' % s for s in sale_ids)} NOT changed)"
            audit(cur, 'prescription.edit', 'prescription', pid, note, before=old_snapshot,
                  after={'doctor': doctor, 'notes': notes, 'medicines': [
                      {'medicine_id': mid, 'dosage': dose, 'days': days} for mid, dose, days in items]})
            mysql.connection.commit()
            for w in allergy_warnings(rx['medical_history'], names):
                flash(w, 'warning')
            flash(f'Prescription #{pid} updated.', 'success')
            return redirect(url_for('prescriptions'))

        cur.execute("""SELECT pi.medicine_id, pi.dosage, pi.duration_days
                       FROM prescription_items pi WHERE pi.prescription_id=%s ORDER BY pi.item_id""", (pid,))
        items = cur.fetchall()
        cur.execute("SELECT medicine_id, name FROM medicines WHERE is_deleted = 0 ORDER BY name")
        meds = cur.fetchall()
        return render_template('edit_prescription.html', rx=rx, items=items, medicines=meds, dispensed=dispensed,
                               sale_ids=sale_ids, doctor_clean=_clean_doctor(rx['doctor_name']))
    except ValueError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('edit_prescription', pid=pid))
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
        return redirect(url_for('prescriptions'))
    finally:
        cur.close()

@app.route('/prescriptions/<int:pid>/delete', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def delete_prescription(pid):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT COUNT(*) AS n FROM sales WHERE prescription_id=%s", (pid,))
        if cur.fetchone()['n']:
            mysql.connection.rollback()
            flash('This prescription was dispensed, so it cannot be deleted. It is part of the sales history.', 'warning')
            return redirect(url_for('prescriptions'))
        cur.execute("""SELECT p.doctor_name, c.name AS customer_name
                       FROM prescriptions p JOIN customers c ON p.customer_id = c.customer_id
                       WHERE p.prescription_id=%s""", (pid,))
        rx = cur.fetchone()
        if not rx:
            flash('Prescription not found', 'danger')
            return redirect(url_for('prescriptions'))
        cur.execute("""SELECT m.name, pi.dosage, pi.duration_days FROM prescription_items pi
                       JOIN medicines m ON pi.medicine_id = m.medicine_id WHERE pi.prescription_id=%s""", (pid,))
        removed_items = cur.fetchall()
        cur.execute("DELETE FROM prescriptions WHERE prescription_id=%s", (pid,))     # items go automatically
        audit(cur, 'prescription.delete', 'prescription', pid, f"{rx['customer_name']} / {doctor_label(rx['doctor_name'])}",
              before={'doctor': rx['doctor_name'], 'customer': rx['customer_name'], 'medicines': removed_items})
        mysql.connection.commit()
        flash(f'Prescription #{pid} deleted.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('prescriptions'))

@app.route('/prescription/receipt/<int:pid>')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def prescription_receipt(pid):
    cur = mysql.connection.cursor()
    cur.execute("""SELECT p.*, c.name AS customer_name, c.contact_number, c.email
                   FROM prescriptions p JOIN customers c ON p.customer_id = c.customer_id
                   WHERE p.prescription_id = %s""", (pid,))
    prescription = cur.fetchone()
    if not prescription:
        cur.close()
        flash('Prescription not found', 'danger')
        return redirect(url_for('prescriptions'))
    cur.execute("""SELECT pi.*, m.name AS medicine_name
                   FROM prescription_items pi JOIN medicines m ON pi.medicine_id = m.medicine_id
                   WHERE pi.prescription_id = %s ORDER BY pi.item_id""", (pid,))
    items = cur.fetchall()
    cur.execute("SELECT sale_id, sale_date, total_amount FROM sales WHERE prescription_id=%s ORDER BY sale_id", (pid,))
    dispensed = cur.fetchall()
    cur.close()
    return render_template('prescription_receipt.html', prescription=prescription, items=items, dispensed=dispensed)
