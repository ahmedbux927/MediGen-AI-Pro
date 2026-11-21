"""Routes: quick sell page and drip and injection record (v77, v84). Admin and Pharmacist only."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.repos import medicines as repo
from pharmacy.services import drip_record as DR
from pharmacy.services import drip_catalog as DC
from pharmacy.services import drip_report as RPT
from pharmacy.lib import _csv_response
from datetime import date as _date, datetime as _dt, timedelta as _td


@app.route('/drip')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def drip():
    return redirect(url_for('products_section', key='drip'))     # v86: Drip & Injection is a product section now


@app.route('/drip/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def drip_add():
    cur = mysql.connection.cursor()
    try:
        DR.ensure_drip_table(cur)
        rec = DR.read_record(request.form)
        cust = {'name': 'walk-in'}
        if rec['customer_id'] is not None:
            cur.execute("SELECT customer_id, name FROM customers WHERE customer_id=%s", (rec['customer_id'],))
            cust = cur.fetchone()
            if not cust:
                raise ValueError('Patient not found.')
        cur.execute("SELECT medicine_id, name, dosage_form, stock_quantity FROM medicines WHERE medicine_id=%s FOR UPDATE",
                    (rec['medicine_id'],))
        med = cur.fetchone()
        if not med:
            raise ValueError('Medicine not found.')
        if not DR.is_drip_form(med['dosage_form']):
            raise ValueError(f"{med['name']} is not an injection or drip. Use a normal sale for it.")
        old = int(med['stock_quantity'] or 0)
        q = rec['quantity']
        if q > old:
            raise ValueError(f"Only {old} units of {med['name']} are in stock.")
        new = old - q
        repo.take_from_batches_fifo(cur, rec['medicine_id'], q)
        repo.set_stock(cur, rec['medicine_id'], new)
        repo.insert_adjustment(cur, rec['medicine_id'], session['user_id'], -q, old, new,
                               'Given to patient', f"Patient: {cust['name']} ({rec['route']})")
        cur.execute("""INSERT INTO drip_injections (medicine_id, customer_id, route, dose_text, quantity, notes, given_by)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (rec['medicine_id'], rec['customer_id'], rec['route'], rec['dose_text'], q, rec['notes'], session['user_id']))
        audit(cur, 'drip.give', 'medicine', rec['medicine_id'],
              f"{med['name']} x{q} to {cust['name']} ({rec['route']}, {rec['dose_text']})")
        mysql.connection.commit()
        flash(f"Recorded: {med['name']} x{q} for {cust['name']}. Stock {old} -> {new}.", 'success')
    except ValueError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('drip record failed')
        flash_unexpected('Something went wrong. Nothing was recorded.')
    finally:
        cur.close()
    return redirect(url_for('drip'))


@app.route('/drip/import', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def drip_import():
    """v85: load the drip and injection list from a CSV. All or nothing."""
    f = request.files.get('catalog')
    if not f or not f.filename:
        flash('Choose a CSV file first.', 'warning')
        return redirect(url_for('drip'))
    items, errors = DC.parse_catalog(f.read(DC.MAX_BYTES + 1))
    if errors:
        flash(errors[0], 'danger')
        return redirect(url_for('drip'))
    cur = mysql.connection.cursor()
    try:
        DR.ensure_drip_table(cur)
        added, skipped = DC.import_items(cur, items, session['user_id'], f.filename)
        audit(cur, 'drip.list_import', 'medicine', None, f"{added} added, {skipped} already there, from {f.filename[:60]}")
        mysql.connection.commit()
        flash(f'List loaded: {added} new item(s) added, {skipped} already in the list (skipped). Set price and stock before selling.', 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('drip list import failed')
        flash_unexpected('The file could not be loaded. Nothing was saved.')
    finally:
        cur.close()
    return redirect(url_for('drip'))


@app.route('/drip/item/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def drip_item_add():
    """v85: add one drip or injection item to the list (price and stock set later)."""
    name = (request.form.get('name') or '').strip()
    strength = (request.form.get('strength') or '').strip()[:100]
    form = (request.form.get('dosage_form') or '').strip()
    if not 2 <= len(name) <= 100:
        flash('Item name must be 2 to 100 characters.', 'danger')
        return redirect(url_for('drip'))
    if form not in DR.DRIP_FORMS:
        flash('Choose Injection or Drip / IV fluid.', 'danger')
        return redirect(url_for('drip'))
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT medicine_id FROM medicines WHERE name=%s", (name,))
        if cur.fetchone():
            flash('This item is already in the list.', 'warning')
            return redirect(url_for('drip'))
        cid = DC._category_id(cur, 'Injections')
        cur.execute("""INSERT INTO medicines (name, category_id, price, cost_price, stock_quantity, reorder_level, strength, dosage_form)
                       VALUES (%s,%s,0,0,0,0,%s,%s)""", (name, cid, strength or None, form))
        audit(cur, 'drip.item_add', 'medicine', cur.lastrowid, f"{name} ({form})")
        mysql.connection.commit()
        flash(f'Added {name}. Set its price in Medicines and add stock by Purchase.', 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('drip item add failed')
        flash_unexpected('The item could not be added.')
    finally:
        cur.close()
    return redirect(url_for('drip'))


@app.route('/drip/item/<int:mid>/remove', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def drip_item_remove(mid):
    """v85: delete a drip or injection item only if it has no sales, stock or records."""
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT name, dosage_form FROM medicines WHERE medicine_id=%s", (mid,))
        med = cur.fetchone()
        if not med or not DR.is_drip_form(med['dosage_form']):
            flash('That item is not in the drip and injection list.', 'warning')
            return redirect(url_for('drip'))
        reason = DC.remove_blocker(cur, mid)
        if reason:
            flash(f"{med['name']}: {reason}", 'warning')
            return redirect(url_for('drip'))
        cur.execute("DELETE FROM medicines WHERE medicine_id=%s", (mid,))
        audit(cur, 'drip.item_remove', 'medicine', mid, med['name'])
        mysql.connection.commit()
        flash(f"Removed {med['name']} from the list.", 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('drip item remove failed')
        flash_unexpected('The item could not be removed. Nothing changed.')
    finally:
        cur.close()
    return redirect(url_for('drip'))


def _day(text, fallback):
    try:
        return _dt.strptime((text or '').strip(), '%Y-%m-%d').date()
    except ValueError:
        return fallback


@app.route('/drip/records')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def drip_records():
    """v85: records between two dates, expiry of drip stock, and a CSV export. Read-only."""
    today = _date.today()
    d_from = _day(request.args.get('from'), today)
    d_to = _day(request.args.get('to'), today)
    if d_to < d_from:
        d_from, d_to = d_to, d_from
    if (d_to - d_from).days > 366:
        d_from = d_to - _td(days=366)
        flash('The report covers at most one year at a time.', 'warning')
    cur = mysql.connection.cursor()
    try:
        rows = RPT.records(cur, d_from, d_to)
        expiry = RPT.expiring_batches(cur)
        totals = {'records': len(rows), 'quantity': sum(int(r['quantity'] or 0) for r in rows)}
        if request.args.get('export') == '1':
            header = ['Date', 'Time', 'Medicine', 'Patient', 'Route', 'Dose', 'Quantity', 'Sale no.', 'Given by', 'Notes']
            data = [[r['given_at'].strftime('%Y-%m-%d'), r['given_at'].strftime('%H:%M'), r['medicine_name'], r['patient'],
                     r['route'], r['dose_text'], r['quantity'], r['sale_id'] or '', r['given_by_name'] or '', r['notes'] or '']
                    for r in rows]
            return _csv_response(header, data, f"drip_records_{d_from}_to_{d_to}.csv")
    finally:
        cur.close()
    return render_template('drip_records.html', rows=rows, expiry=expiry, totals=totals,
                           d_from=d_from, d_to=d_to, today=today)
