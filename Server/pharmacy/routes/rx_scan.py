"""Routes: prescription photo intake (v76). Staff upload a photo, check suggested rows, then save.
Nothing is saved until the pharmacist ticks the check box on the review page."""
from flask import send_file, abort

from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _customer_or_error, _read_prescription_form, _save_items
from pharmacy.services import rx_scan as RXS


@app.route('/prescriptions/scan', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def rx_scan():
    cur = mysql.connection.cursor()
    try:
        if request.method == 'GET':
            cur.execute("SELECT customer_id, name, medical_history FROM customers ORDER BY name")
            return render_template('rx_scan.html', customers=cur.fetchall(), ocr=RXS.ocr_status())   # v87.06
        cust = _customer_or_error(cur, request.form.get('customer_id'))
        # v86.16: camera input (photo_cam) or gallery input (photo); take whichever was filled
        f = next((x for x in (request.files.get('photo_cam'), request.files.get('photo'))
                  if x and x.filename), None)
        if not f:
            raise ValueError('Please choose a photo of the prescription.')
        data = f.stream.read(RXS.MAX_BYTES + 1)
        if len(data) > RXS.MAX_BYTES:
            raise ValueError('The photo is larger than 5 MB. Take it again, a bit closer.')
        ext = RXS.sniff_type(data)
        if not ext:
            raise ValueError('Only JPG, PNG or WEBP photos are allowed.')
        token = RXS.save_upload(data, ext)
        provider, lines, note = RXS.extract_lines(RXS.image_path(token))
        cur.execute("""SELECT m.medicine_id, m.name, m.stock_quantity,
                              IFNULL((SELECT SUM(b.quantity) FROM batches b
                                      WHERE b.medicine_id = m.medicine_id AND b.quantity > 0 AND b.expiry_date >= CURDATE()), 0) AS fresh_qty,
                              (SELECT COUNT(*) FROM batches b2 WHERE b2.medicine_id = m.medicine_id) AS batch_count
                       FROM medicines m WHERE m.is_deleted = 0 ORDER BY m.name""")
        meds = cur.fetchall()
        for m in meds:   # v86.16: same availability rule as the sale screen
            m['available'] = (min(int(m['stock_quantity']), int(m['fresh_qty'])) if m['batch_count']
                              else int(m['stock_quantity'] or 0))
        rows = RXS.suggest(lines, [(m['medicine_id'], m['name']) for m in meds])
        cur.execute("SELECT name FROM customers WHERE customer_id=%s", (cust['customer_id'],))
        cust_name = (cur.fetchone() or {}).get('name', '')
        return render_template('rx_review.html', token=token, cust=cust, cust_name=cust_name, rows=rows,
                               medicines=meds, note=note, provider=provider)
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('rx_scan'))
    except Exception:
        app.logger.exception('prescription photo failed')
        flash_unexpected('The photo could not be read. Please try again.')
        return redirect(url_for('rx_scan'))
    finally:
        cur.close()


@app.route('/prescriptions/scan/image/<token>')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def rx_scan_image(token):
    path = RXS.image_path(token)
    if not path:
        abort(404)
    resp = send_file(path, mimetype=RXS.mime_for(path))
    resp.headers['Cache-Control'] = 'private, no-store'
    return resp


@app.route('/prescriptions/scan/save', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def rx_scan_save():
    token = request.form.get('token', '')
    if not RXS.image_path(token):
        flash('This photo review has expired. Please upload the photo again.', 'warning')
        return redirect(url_for('rx_scan'))
    if request.form.get('confirmed') != '1':
        flash('Nothing was saved. Tick the box to confirm you checked every item against the paper.', 'warning')
        return redirect(url_for('rx_scan'))
    cur = mysql.connection.cursor()
    try:
        cust = _customer_or_error(cur, request.form.get('customer_id'))
        doctor, notes, items, names = _read_prescription_form(cur, request.form)
        cur.execute("INSERT INTO prescriptions (customer_id, doctor_name, date_issued, notes) VALUES (%s,%s,CURDATE(),%s)",
                    (cust['customer_id'], doctor, notes))
        pid = cur.lastrowid
        _save_items(cur, pid, items)
        audit(cur, 'prescription.scan_add', 'prescription', pid, f"{doctor}, {len(items)} medicine(s), from photo")
        mysql.connection.commit()
        RXS.delete(token)
        for w in allergy_warnings(cust['medical_history'], names):
            flash(w, 'warning')
        flash(f'Prescription #{pid} saved from the photo.', 'success')
        if request.form.get('then_bill') == '1':   # v86.16: open the sale with the in-stock items only
            return redirect(url_for('new_sale', rx=pid))
        return redirect(url_for('prescriptions'))
    except ValueError as e:
        mysql.connection.rollback()
        flash(str(e) + ' The photo is kept for 1 hour, so you can fix the rows and save again.', 'danger')
        return redirect(url_for('rx_scan'))
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('prescription from photo failed')
        flash_unexpected('Something went wrong. Nothing was saved.')
        return redirect(url_for('rx_scan'))
    finally:
        cur.close()


@app.route('/prescriptions/scan/cancel', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def rx_scan_cancel():
    RXS.delete(request.form.get('token', ''))
    flash('Photo review cancelled. Nothing was saved.', 'info')
    return redirect(url_for('rx_scan'))
