"""Routes: medicines. SQL lives in pharmacy/repos/medicines.py."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _csv_response, _like, _read_medicine_form
from pharmacy.repos import medicines as repo
from pharmacy.services import product_sections as PS


@app.route('/medicines')
@login_required
@guarded
def medicines():
    q = request.args.get('q', '').strip()[:60]
    flt = request.args.get('filter', 'all')
    page = max(1, request.args.get('page', 1, type=int))
    per = 100000   # v86.26: every item on one page (no 15/50/100)
    if flt not in ('low', 'out', 'ok'):
        flt = 'all'

    cur = mysql.connection.cursor()
    listing = repo.list_medicines(cur, _like(q) if q else '', flt, page, per)
    # v86.53: this page shows only the Medicines section (tablets, capsules, powders...).
    # Syrups, creams, drip/injection and bandages stay on their own section pages.
    listing['rows'] = [r for r in listing['rows'] if PS.section_for(r.get('dosage_form')) == 'medicines']
    issue = request.args.get('issue', '')          # v86.62: opened from Data Quality ("No category" list)
    if issue == 'nocat':
        listing['rows'] = [r for r in listing['rows'] if r.get('category_id') is None]
    listing['total'] = len(listing['rows'])
    listing['pages'] = 1
    listing['page'] = 1
    listing['offset'] = 0
    everything = [r for r in repo.list_medicines(cur, '', 'all', 1, per)['rows']
                  if PS.section_for(r.get('dosage_form')) == 'medicines']
    stk = lambda r: int(r.get('stock_quantity') or 0)
    stats = {'total': len(everything),
             'in_stock': sum(1 for r in everything if stk(r) > 0),
             'low': sum(1 for r in everything if 0 < stk(r) <= int(r.get('reorder_level') or 0)),
             'empty': sum(1 for r in everything if stk(r) <= 0)}
    cats = repo.list_categories_by_name(cur)
    # v86.35: barcodes already in use, so the Add form can warn at once when a scan is a duplicate
    barcode_map = repo.barcode_map(cur)
    cur.close()
    stats['categories'] = len(cats)
    section_cats = set(PS.SECTION_CATEGORY.values()) - {'Medicines'}   # v86.27: Syrups, Creams, Injections, Bandages
    med_cats = [c for c in cats if c['category_name'] not in section_cats]
    cat_names = {c['category_id']: c['category_name'] for c in cats}

    return render_template('medicines.html', medicines=listing['rows'], categories=med_cats, cat_names=cat_names,
                           stats=stats, q=q, flt=flt, page=listing['page'], pages=listing['pages'],
                           per=per, total=listing['total'], offset=listing['offset'],
                           adjust_reasons=ADJUST_REASONS, dosage_forms=MEDICINE_FORMS, barcode_map=barcode_map,
                           all_categories=cats, bulk_forms=list(dict.fromkeys(MEDICINE_FORMS + PS.ALL_FORM_CHOICES)),
                           issue=issue)

@app.route('/medicines/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def add_medicine():
    data, err = _read_medicine_form(request.form)
    try:
        stock = int(request.form.get('stock') or 0)
    except ValueError:
        err, stock = 'Invalid number format', 0
    if not err and stock < 0:
        err = 'Stock cannot be negative'
    if err:
        flash(err, 'danger')
        return redirect(url_for('medicines'))

    cur = mysql.connection.cursor()
    try:
        if repo.find_same_product(cur, data['name']):          # v86.54: same name + strength is an error
            flash(repo.duplicate_message(data['name']), 'danger')
            return redirect(url_for('medicines'))
        if data['barcode'] and repo.find_medicine_by_barcode(cur, data['barcode']):
            flash('This barcode is already used by another medicine.', 'warning')
            return redirect(url_for('medicines'))
        new_id = repo.insert_medicine(cur, data, stock)
        if stock > 0:
            repo.insert_opening_stock(cur, new_id, session['user_id'], stock)
        audit(cur, 'medicine.add', 'medicine', None, data['name'])
        mysql.connection.commit()
        flash('Medicine added successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Medicine could not be added.', code=ERROR_CODES['medicine_add'])
    finally:
        cur.close()
    return redirect(url_for('medicines'))

@app.route('/medicines/edit/<int:mid>', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def edit_medicine(mid):
    data, err = _read_medicine_form(request.form)
    if err:
        flash(err, 'danger')
        return redirect(url_for('medicines'))
    cur = mysql.connection.cursor()
    try:
        if repo.find_same_product(cur, data['name'], exclude_id=mid):   # v86.54
            flash(repo.duplicate_message(data['name']), 'danger')
            return redirect(url_for('medicines'))
        if data['barcode'] and repo.find_medicine_by_barcode(cur, data['barcode'], exclude_id=mid):
            flash('This barcode is already used by another medicine.', 'warning')
            return redirect(url_for('medicines'))
        repo.update_medicine(cur, mid, data)
        audit(cur, 'medicine.edit', 'medicine', mid, data['name'])
        mysql.connection.commit()
        flash('Medicine updated successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(request.referrer or url_for('medicines'))

@app.route('/medicines/adjust/<int:mid>', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def adjust_stock(mid):
    direction = request.form.get('direction', '')
    reason = request.form.get('reason', '')
    note = request.form.get('note', '').strip()[:255]
    try:
        qty = int(request.form.get('quantity', '0'))
    except ValueError:
        qty = 0
    if direction not in ADJUST_REASONS or reason not in ADJUST_REASONS[direction] or qty <= 0:
        flash('Please choose in/out, a reason and a quantity above 0', 'danger')
        return redirect(request.referrer or url_for('medicines'))

    cur = mysql.connection.cursor()
    try:
        med = repo.lock_medicine(cur, mid)
        if not med:
            flash('Medicine not found', 'danger')
            return redirect(url_for('medicines'))
        old = med['stock_quantity']

        if direction == 'out':
            if qty > old:
                mysql.connection.rollback()
                flash(f"Only {old} units of {med['name']} are in stock", 'danger')
                return redirect(request.referrer or url_for('medicines'))
            new, change = old - qty, -qty
            # take the units out of the batches too, oldest expiry first
            repo.take_from_batches_fifo(cur, mid, qty)
        else:
            new, change = old + qty, qty

        repo.set_stock(cur, mid, new)
        repo.insert_adjustment(cur, mid, session['user_id'], change, old, new, reason, note or None)
        audit(cur, 'stock.adjust', 'medicine', mid, f"{med['name']}: {old} -> {new} ({reason})")
        mysql.connection.commit()
        flash(f"Stock of {med['name']} changed: {old} -> {new}", 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(request.referrer or url_for('medicines'))

@app.route('/medicines/<int:mid>/adjustments')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def stock_history(mid):
    cur = mysql.connection.cursor()
    rows = repo.stock_history(cur, mid)
    cur.close()
    return jsonify([{'when': str(r['created_at'])[:16], 'change': r['change_qty'], 'old': r['old_stock'],
                     'new': r['new_stock'], 'reason': r['reason'], 'note': r['note'] or '',
                     'by': r['full_name'] or '-'} for r in rows])

@app.route('/medicines/delete/<int:mid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def delete_medicine(mid):
    cur = mysql.connection.cursor()
    try:
        repo.purge_medicine(cur, mid)              # v86.29: hidden from every list; bills keep their rows
        audit(cur, 'medicine.delete', 'medicine', mid, '')
        mysql.connection.commit()
        flash('Medicine deleted', 'success')
    except Exception as e:
        mysql.connection.rollback()
        if e.args and e.args[0] == 1451:
            flash('This medicine is still linked to other records, so it cannot be deleted.', 'warning')
        else:
            flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('medicines'))


@app.route('/medicines/bulk-delete', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def bulk_delete_medicines():
    """v86.34: hides every ticked medicine (same rule as the single delete)."""
    ids = list(dict.fromkeys(int(x) for x in request.form.getlist('mid') if x.isdigit()))
    back = request.form.get('next', '')
    if not back.startswith('/products/') or back.startswith('//'):   # v86.36: return to the section page
        back = url_for('medicines')
    if not ids:
        flash('No medicine was selected.', 'warning')
        return redirect(back)
    cur = mysql.connection.cursor()
    try:
        for mid in ids:
            repo.purge_medicine(cur, mid)
        audit(cur, 'medicine.bulk_delete', 'medicine', 0, f'{len(ids)} medicine(s): ' + ','.join(str(i) for i in ids[:50]))
        mysql.connection.commit()
        flash(f'{len(ids)} medicine(s) deleted.', 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('bulk delete failed')
        flash_unexpected('Nothing was deleted.')
    finally:
        cur.close()
    return redirect(back)


@app.route('/medicines/bulk-edit', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def bulk_edit_medicines():
    """v86.41: edit every ticked item at once. Only the fields that are filled in change; blank means no change."""
    import datetime as _dt
    ids = list(dict.fromkeys(int(x) for x in request.form.getlist('mid') if x.isdigit()))
    back = request.form.get('next', '')
    if not (back.startswith('/medicines') or back.startswith('/products/')):
        back = url_for('medicines')
    if not ids:
        flash('No item was selected.', 'warning')
        return redirect(back)
    cat_raw = (request.form.get('category_id') or '').strip()
    form_raw = (request.form.get('dosage_form') or '').strip()
    price_raw = (request.form.get('price') or '').strip()
    exp_raw = (request.form.get('expiry') or '').strip()
    strength = (request.form.get('strength') or '').strip()[:60] or None   # v86.45
    if not (cat_raw or form_raw or price_raw or exp_raw or strength):
        flash('Nothing to change. Fill at least one field.', 'warning')
        return redirect(back)
    try:
        category_id = int(cat_raw) if cat_raw else None
        dosage_form = None
        if form_raw:
            if form_raw not in set(MEDICINE_FORMS) | set(PS.ALL_FORM_CHOICES):
                raise ValueError('That dosage form is not in the list.')
            dosage_form = form_raw
        price = None
        if price_raw:
            price = float(price_raw)
            if price < 0:
                raise ValueError('Price cannot be negative.')
        expiry = _dt.date.fromisoformat(exp_raw) if exp_raw else None
    except ValueError as e:
        flash(str(e) if str(e) else 'Check the values you entered.', 'danger')
        return redirect(back)
    cur = mysql.connection.cursor()
    try:
        if category_id or dosage_form or price is not None or strength:
            repo.bulk_update_fields(cur, ids, category_id, dosage_form, price, strength)
        exp_info = None
        if expiry:
            exp_info = repo.bulk_update_expiry(cur, ids, expiry)
        parts = [f'{k}={v}' for k, v in (('category', category_id), ('dosage_form', dosage_form), ('strength', strength),
                                          ('price', price), ('expiry', expiry)) if v not in (None, '')]
        audit(cur, 'medicine.bulk_edit', 'medicine', 0, f'{len(ids)} item(s): ' + ', '.join(parts))
        mysql.connection.commit()
        msg = f'{len(ids)} item(s) updated.'
        if exp_info:
            msg += f" Expiry: {exp_info['updated']} batch(es) changed, {exp_info['created']} item(s) got a new batch from their stock."
            if exp_info['skipped']:
                msg += f" {exp_info['skipped']} item(s) have no stock, so no expiry was set. Set it after receiving stock."
            flash(msg, 'success')
        else:
            flash(msg, 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('bulk edit failed')
        flash_unexpected('Nothing was changed.')
    finally:
        cur.close()
    return redirect(back)


@app.route('/medicines/export')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def export_medicines():
    """CSV of all medicines, or only the ones selected on the medicines page (?ids=1,2,3)."""
    cur = mysql.connection.cursor()
    try:
        ids = [int(x) for x in request.args.get('ids', '').split(',') if x.strip().isdigit()]
        rows = []
        for r in repo.export_medicine_rows(cur, ids):
            stock = int(r['stock_quantity'] or 0)
            reorder = int(r['reorder_level'] or 0)
            status = 'Out of stock' if stock <= 0 else ('Low stock' if stock <= reorder else 'OK')
            rows.append((r['name'], r['category_name'] or '',
                         r['price'], '' if session.get('role') == 'Cashier' else r['cost_price'], stock, reorder, status))
        return _csv_response(['Medicine', 'Category', 'Price (Rs.)', 'Cost (Rs.)',
                              'Stock', 'Reorder level', 'Status'], rows,
                             f'medicines_{datetime.now().strftime("%Y%m%d_%H%M")}.csv')
    except Exception as e:
        app.logger.exception('medicine export failed')
        flash_unexpected('Could not export medicines.')
        return redirect(url_for('medicines'))
    finally:
        cur.close()
