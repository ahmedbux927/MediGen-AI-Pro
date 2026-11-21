"""v86: product sections (Medicines, Syrups, Creams & Gels, Drip & Injection, Bandages & Other), the sale cart,
edit, CSV load, add one item and remove one item. Everyone who sells can add to the cart; changes are Admin and Pharmacist."""
import io
import re
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import product_sections as PS
from pharmacy.services import product_import as PIMP   # Stage 5: plan-based import (preview/confirm/undo)
import json as _json
from decimal import Decimal as _Decimal
from pharmacy.services import drip_catalog as DC
from pharmacy.services import drip_record as DR
from pharmacy.lib import _csv_response
from pharmacy.repos import medicines as repo
from datetime import date as _date

CART_KEY = 'sale_cart'
CART_MAX_LINES = 40
ALL_FORMS = None


def _forms():
    return list(MEDICINE_FORMS)


def _cart():
    return list(session.get(CART_KEY) or [])


def _save_cart(cart):
    session[CART_KEY] = cart
    session.modified = True


from pharmacy.repos import medicines as MREPO  # v86.27


def _back(key):
    return redirect(url_for('products_section', key=key) if key in PS.SECTION_KEYS else url_for('products_hub'))


def _section_rows(cur, key):
    cur.execute("""SELECT m.medicine_id, m.name, m.barcode, m.generic_name, m.strength, m.dosage_form, m.price,
                          m.stock_quantity, m.reorder_level,
                          (SELECT MIN(b.expiry_date) FROM batches b WHERE b.medicine_id = m.medicine_id AND b.quantity > 0) AS next_expiry
                   FROM medicines m WHERE m.is_deleted = 0 ORDER BY m.name""")
    rows = [r for r in cur.fetchall() if PS.section_for(r['dosage_form']) == key]
    for r in rows:
        r['stock'] = int(r['stock_quantity'] or 0)
    return rows


@app.route('/products')
@login_required
@guarded
def products_hub():
    cur = mysql.connection.cursor()
    try:
        DR.ensure_drip_table(cur)
        ov = PS.overview(cur)
    finally:
        cur.close()
    cards = [{'key': k, 'label': lab, 'icon': ic, 'desc': desc, **ov[k]} for k, lab, ic, desc in PS.SECTIONS]
    return render_template('products_hub.html', cards=cards, cart=_cart())


@app.route('/products/<key>')
@login_required
@guarded
def products_section(key):
    if key not in PS.SECTION_KEYS:
        flash('That section does not exist.', 'warning')
        return redirect(url_for('products_hub'))
    q = (request.args.get('q') or '').strip()[:60]
    code = (request.args.get('code') or '').strip()[:60]
    cur = mysql.connection.cursor()
    try:
        rows = _section_rows(cur, key)
        if code:                                   # barcode scan: add one piece to the sale cart
            hit = next((r for r in rows if r['barcode'] == code), None)
            if hit is None:
                cur.execute("SELECT medicine_id, dosage_form FROM medicines WHERE barcode=%s AND is_deleted = 0 LIMIT 1", (code,))
                other = cur.fetchone()
                if other:
                    return redirect(url_for('products_section', key=PS.section_for(other['dosage_form'])) + f'?code={code}')
                flash(f'No product has barcode {code}.', 'warning')
                return redirect(url_for('products_section', key=key))
            return _add_to_cart(hit['medicine_id'], 1, key, hit['stock'], hit['name'])
    finally:
        cur.close()
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in (r['name'] or '').lower() or ql in (r['generic_name'] or '').lower()
                or ql in (r['barcode'] or '')]
    cart = _cart()
    try:
        per = int(request.args.get('per') or 15)
    except ValueError:
        per = 15
    per = 100000   # v86.26: every item on one page
    horizon = _date.today().toordinal() + 60
    stats = {
        'total': len(rows),
        'in_stock': sum(1 for x in rows if x['stock'] > 0),
        'low': sum(1 for x in rows if 0 < x['stock'] <= int(x['reorder_level'] or 0)),
        'out': sum(1 for x in rows if x['stock'] <= 0),
        'expiring': sum(1 for x in rows if x['next_expiry'] and x['next_expiry'].toordinal() <= horizon),
    }
    for x in rows:   # v86.37: stat cards filter the list (expiring flag per row)
        x['exp_soon'] = bool(x['next_expiry'] and x['next_expiry'].toordinal() <= horizon)
    total = len(rows)
    pages = max(1, -(-total // per))
    try:
        page = min(max(1, int(request.args.get('page') or 1)), pages)
    except ValueError:
        page = 1
    shown = rows[(page - 1) * per: page * per]
    pager = {'page': page, 'pages': pages, 'per': per, 'total': total,
             'from': (page - 1) * per + 1 if total else 0, 'to': min(page * per, total)}
    cur2 = mysql.connection.cursor()   # v86.41: categories for the bulk edit popup
    try:
        all_cats = repo.list_categories_by_name(cur2)
    finally:
        cur2.close()
    return render_template('products.html', key=key, label=PS.SECTION_LABEL[key], rows=shown, q=q,
                           all_categories=all_cats, bulk_forms=list(dict.fromkeys(PS.ALL_FORM_CHOICES)),
                           cart=cart, forms=PS.FORM_CHOICES[key], sections=PS.SECTIONS, pager=pager, stats=stats,
                           icon=next(ic for k, lab, ic, desc in PS.SECTIONS if k == key))


def _add_to_cart(mid, qty, key, stock, name):
    cart = _cart()
    current = next((c for c in cart if c['mid'] == mid), None)
    have = (current['qty'] if current else 0)
    if have + qty > stock:
        flash(f'Only {stock} in stock for {name}. Already in sale: {have}.', 'warning')
        return _back(key)
    if current:
        current['qty'] = have + qty
    else:
        if len(cart) >= CART_MAX_LINES:
            flash(f'A sale can have at most {CART_MAX_LINES} items.', 'warning')
            return _back(key)
        cart.append({'mid': mid, 'qty': qty, 'name': name})
    _save_cart(cart)
    flash(f'Added {name} x{qty}. Items in sale: {len(cart)}.', 'success')
    return redirect(url_for('new_sale'))          # every add lands in the sale screen


@app.route('/cart/add', methods=['POST'])
@login_required
@guarded
def cart_add():
    key = request.form.get('key', '')
    try:
        mid = int(request.form.get('mid', ''))
        qty = int(request.form.get('qty', '1') or 1)
    except ValueError:
        flash('Choose a product and a whole-number quantity.', 'danger')
        return _back(key)
    if not 1 <= qty <= 50:
        flash('Quantity must be between 1 and 50.', 'danger')
        return _back(key)
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT name, stock_quantity FROM medicines WHERE medicine_id=%s", (mid,))
        med = cur.fetchone()
    finally:
        cur.close()
    if not med or int(med['stock_quantity'] or 0) <= 0:
        flash('That product is out of stock.', 'warning')
        return _back(key)
    return _add_to_cart(mid, qty, key, int(med['stock_quantity']), med['name'])


@app.route('/cart/add-selected', methods=['POST'])
@login_required
@guarded
def cart_add_selected():
    """One click: every ticked product goes into the sale cart (1 piece each), then the sale screen opens."""
    key = request.form.get('key', '')
    ids = []
    for raw in request.form.getlist('mid'):
        if raw.isdigit() and int(raw) not in ids:
            ids.append(int(raw))
    if not ids:
        flash('Tick at least one product first.', 'warning')
        return _back(key)
    cart = _cart()
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT medicine_id, name, stock_quantity FROM medicines WHERE medicine_id IN (%s)"
                    % ','.join(['%s'] * len(ids)), tuple(ids))
        found = {r['medicine_id']: r for r in cur.fetchall()}
    finally:
        cur.close()
    added, problems = 0, []
    for mid in ids:
        m = found.get(mid)
        if not m:
            continue
        current = next((c for c in cart if c['mid'] == mid), None)
        have = current['qty'] if current else 0
        if have + 1 > int(m['stock_quantity'] or 0):
            problems.append(m['name'])
            continue
        if current:
            current['qty'] = have + 1
        elif len(cart) < CART_MAX_LINES:
            cart.append({'mid': mid, 'qty': 1, 'name': m['name']})
        else:
            problems.append(m['name'])
            continue
        added += 1
    _save_cart(cart)
    if problems:
        flash(f"Added {added}. No stock or sale full for: {', '.join(problems[:5])}", 'warning')
    else:
        flash(f'{added} item(s) added to the sale.', 'success')
    return redirect(url_for('new_sale'))


@app.route('/cart/remove/<int:mid>', methods=['POST'])
@login_required
@guarded
def cart_remove(mid):
    _save_cart([c for c in _cart() if c['mid'] != mid])
    return redirect(request.form.get('next') or url_for('products_hub'))


@app.route('/cart/clear', methods=['POST'])
@login_required
@guarded
def cart_clear():
    session.pop(CART_KEY, None)
    return redirect(request.form.get('next') or url_for('products_hub'))


PDF_MAX_BYTES = 10 * 1024 * 1024   # v86.44


@app.route('/products/<key>/import', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_import(key):
    """v86.43: a CSV, a PDF, or a photo (camera or gallery) of a list. Bad rows are skipped and reported; good rows load."""
    from pharmacy.services import rx_scan as RXS
    if key not in PS.SECTION_KEYS:
        return redirect(url_for('products_hub'))
    f = request.files.get('catalog') or request.files.get('catalog_cam')
    if not f or not f.filename:
        flash('Choose a CSV, PDF or photo first.', 'warning')
        return _back(key)
    name_l = f.filename.lower()
    is_photo = name_l.endswith(('.jpg', '.jpeg', '.png', '.webp'))
    if is_photo:
        data = f.stream.read(RXS.MAX_BYTES + 1)
        if len(data) > RXS.MAX_BYTES:
            flash('The photo is larger than 5 MB. Take it again a little closer, or use a smaller picture.', 'warning')
            return _back(key)
        ext = RXS.sniff_type(data)
        if not ext:
            flash('Only JPG, PNG or WEBP photos are allowed.', 'warning')
            return _back(key)
        token = RXS.save_upload(data, ext)
        try:
            provider, lines, note = RXS.extract_lines(RXS.image_path(token))
        finally:
            RXS.delete(token)
        if provider == 'none':
            flash('To read a photo, this computer needs the free OCR program (Tesseract). '
                  'Install guide: TESSERACT_INSTALL_ROMAN_URDU.md. Until then, use a CSV or PDF.', 'warning')
            return _back(key)
        if not lines:
            flash(note or 'No text was found in the photo. Take a clearer photo, straight from above.', 'warning')
            return _back(key)
        raw, kept = PS.photo_lines_to_csv(lines)
        if not kept:
            flash('The photo was read, but no medicine names were found. Check the photo, or type the names.', 'warning')
            return _back(key)
    else:
        if name_l.endswith('.pdf'):
            raw = f.read(PDF_MAX_BYTES + 1)     # v86.44: scanned PDFs are bigger than a CSV
            if len(raw) > PDF_MAX_BYTES:
                flash('The PDF is larger than 10 MB. Split it into smaller parts.', 'warning')
                return _back(key)
            raw, errors = PS.pdf_to_csv_bytes(raw)
            if errors:
                flash(errors[0], 'danger')
                return _back(key)
        elif name_l.endswith('.csv'):
            raw = f.read(PS.MAX_BYTES + 1)
        else:
            flash('Choose a CSV, PDF or photo (JPG, PNG, WEBP).', 'warning')
            return _back(key)
    items, errors, warnings = PS.parse_products_report(raw, key)
    if errors:
        flash(errors[0], 'danger')
        return _back(key)
    cur = mysql.connection.cursor()
    try:
        added, skipped = PS.import_items(cur, items, key, session['user_id'], f.filename)
        audit(cur, 'products.import', 'medicine', None, f"{key}: {added} added, {skipped} already there, from {f.filename[:60]}")
        mysql.connection.commit()
        msg = f'List loaded: {added} new item(s), {skipped} already in the list (skipped). Set price and add stock by Purchase.'
        flash(msg, 'success')
        if warnings:
            more = f' and {len(warnings) - 3} more' if len(warnings) > 3 else ''
            flash('Some lines were skipped: ' + ' | '.join(warnings[:3]) + more, 'warning')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('products import failed')
        flash_unexpected('The file could not be loaded. Nothing was saved.')
    finally:
        cur.close()
    return _back(key)


# ---------- Stage 12: barcode label printing ----------
@app.route('/products/labels')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def product_labels():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT medicine_id, name, barcode, price FROM medicines
                   WHERE is_deleted = 0 ORDER BY (barcode IS NULL OR barcode=''), name""")
    meds = cur.fetchall()
    cur.close()
    return render_template('product_labels.html', meds=meds)


@app.route('/products/labels/print', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def product_labels_print():
    ids = request.form.getlist('medicine_id')
    try:
        copies = int(request.form.get('copies') or 1)
    except ValueError:
        copies = 1
    if not ids:
        flash('Pehle kam az kam aik item chunein.', 'warning')
        return redirect(url_for('product_labels'))
    cur = mysql.connection.cursor()
    marks = ','.join(['%s'] * len(ids))
    cur.execute(f"SELECT name, barcode, price FROM medicines WHERE medicine_id IN ({marks}) AND is_deleted = 0",
                [int(i) for i in ids if str(i).isdigit()])
    rows = cur.fetchall()
    cur.close()
    from pharmacy.services.labels_pdf import build_labels_pdf
    items = [dict(r, copies=copies) for r in rows if (r.get('barcode') or '').strip()]
    if not items:
        flash('Chune hue items me kisi ke paas barcode nahi. Pehle Edit page se barcode set karein.', 'warning')
        return redirect(url_for('product_labels'))
    pdf = build_labels_pdf(items)
    from flask import send_file
    return send_file(io.BytesIO(pdf), mimetype='application/pdf',
                     as_attachment=True, download_name='barcode-labels.pdf')


# ---------- Stage 5: import with preview, confirm and undo ----------
def _import_existing(cur):
    cur.execute("SELECT medicine_id, name, barcode, stock_quantity FROM medicines WHERE is_deleted = 0")
    rows = cur.fetchall()
    return {'barcodes': {r['barcode']: r for r in rows if r['barcode']},
            'names': {PIMP.name_key(r['name']): r for r in rows}}


@app.route('/products/import-preview', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def import_preview():
    cur = mysql.connection.cursor()
    try:
        if request.method == 'POST':
            f = request.files.get('import_file')
            if not f or not f.filename:
                flash('Choose a CSV, Excel or PDF file first.', 'warning')
                return redirect(url_for('import_preview'))
            name_l = f.filename.lower()
            if name_l.endswith('.pdf'):
                raw = f.read(PDF_MAX_BYTES + 1)
                if len(raw) > PDF_MAX_BYTES:
                    flash('The PDF is larger than 10 MB. Split it into smaller parts.', 'warning')
                    return redirect(url_for('import_preview'))
                csv_raw, errors = PS.pdf_to_csv_bytes(raw)
                if errors:
                    flash(errors[0], 'danger')
                    return redirect(url_for('import_preview'))
                rows, hwarn = PIMP.read_file(csv_raw, 'import.csv')
            elif name_l.endswith(('.csv', '.xlsx')):
                rows, hwarn = PIMP.read_file(f.read(PS.MAX_BYTES + 1), f.filename)
            else:
                flash('Choose a CSV, Excel (.xlsx) or PDF file.', 'warning')
                return redirect(url_for('import_preview'))
            update_existing = bool(request.form.get('update_existing'))
            plan, summary = PIMP.build_plan(rows, _import_existing(cur), _date.today(), update_existing)
            cur.execute("""INSERT INTO import_previews (user_id, filename, update_existing, plan_json, summary_json)
                           VALUES (%s,%s,%s,%s,%s)""",
                        (session['user_id'], f.filename[:160], 1 if update_existing else 0,
                         _json.dumps(plan, default=str), _json.dumps(summary, default=str)))
            preview_id = cur.lastrowid
            audit(cur, 'products.import_preview', 'import', preview_id,
                  f"{f.filename[:60]}: {summary['counts']} (not saved yet)")
            mysql.connection.commit()
            if hwarn:
                flash(hwarn[0], 'warning')
            return redirect(url_for('import_preview_detail', preview_id=preview_id))
        cur.execute("""SELECT batch_id, filename, summary_json, status, created_at FROM import_batches
                       WHERE user_id=%s ORDER BY batch_id DESC LIMIT 10""", (session['user_id'],))
        batches = cur.fetchall()
        for b in batches:
            b['summary'] = _json.loads(b['summary_json'] or '{}')
        return render_template('import_preview.html', batches=batches)
    except ValueError as e:
        mysql.connection.rollback()
        flash(f'The file could not be read: {e}', 'danger')
        return redirect(url_for('import_preview'))
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('import preview failed')
        flash_unexpected('The file could not be loaded. Nothing was saved.')
        return redirect(url_for('import_preview'))
    finally:
        cur.close()


@app.route('/products/import-preview/<int:preview_id>')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def import_preview_detail(preview_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM import_previews WHERE preview_id=%s", (preview_id,))
    pv = cur.fetchone()
    cur.close()
    if not pv:
        flash('That import preview was not found.', 'warning')
        return redirect(url_for('import_preview'))
    plan = _json.loads(pv['plan_json'])
    for item in plan:   # dates were stored as text; show them as-is
        item['row'] = item.get('row') or {}
    return render_template('import_preview_detail.html', pv=pv, plan=plan,
                           summary=_json.loads(pv['summary_json']))


@app.route('/products/import-preview/<int:preview_id>/confirm', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def import_preview_confirm(preview_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM import_previews WHERE preview_id=%s FOR UPDATE", (preview_id,))
        pv = cur.fetchone()
        if not pv or pv['status'] != 'preview':
            flash('This preview was already used. Upload the file again for a fresh preview.', 'warning')
            return redirect(url_for('import_preview'))
        plan = _json.loads(pv['plan_json'])
        # snapshot the fields an update can change, so the batch can be undone
        snapshot = {}
        for item in plan:
            if item['action'] == 'update' and item.get('medicine_id'):
                cur.execute("""SELECT price, cost_price, reorder_level, generic_name, manufacturer, strength,
                                      dosage_form, rx_required, product_code, category_id, import_source
                               FROM medicines WHERE medicine_id=%s""", (item['medicine_id'],))
                old = cur.fetchone()
                if old:
                    snapshot[str(item['medicine_id'])] = {k: (str(v) if isinstance(v, _Decimal) else v)
                                                          for k, v in old.items()}
        created_ids = []

        def _audit_and_track(cur_, action, entity, entity_id, details, before=None, after=None):
            if action == 'medicine.import' and entity_id:
                created_ids.append(entity_id)
            return audit(cur_, action, entity, entity_id, details, before=before, after=after)

        done = PIMP.apply_plan(cur, plan, pv['filename'][:60], audit_fn=_audit_and_track)
        cur.execute("""INSERT INTO import_batches (preview_id, user_id, filename, created_ids, updated_snapshot, summary_json)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (preview_id, session['user_id'], pv['filename'],
                     _json.dumps(created_ids), _json.dumps(snapshot), pv['summary_json']))
        batch_id = cur.lastrowid
        cur.execute("UPDATE import_previews SET status='confirmed' WHERE preview_id=%s", (preview_id,))
        audit(cur, 'products.import_confirm', 'import', batch_id,
              f"{pv['filename'][:60]}: {done['created']} created, {done['updated']} updated")
        mysql.connection.commit()
        errors = _json.loads(pv['summary_json'])['counts'].get('error', 0)
        msg = f"Import saved: {done['created']} new item(s), {done['updated']} updated."
        if errors:
            msg += f" {errors} row(s) with errors were not imported."
        flash(msg, 'success')
        return redirect(url_for('import_preview'))
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('import confirm failed')
        flash_unexpected('The import failed. Nothing was saved.')
        return redirect(url_for('import_preview'))
    finally:
        cur.close()


@app.route('/products/import-batch/<int:batch_id>/undo', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def import_batch_undo(batch_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM import_batches WHERE batch_id=%s FOR UPDATE", (batch_id,))
        batch = cur.fetchone()
        if not batch or batch['status'] != 'applied':
            flash('This import was already undone or not found.', 'warning')
            return redirect(url_for('import_preview'))
        created_ids = _json.loads(batch['created_ids'] or '[]')
        blocked = []
        for mid in created_ids:
            cur.execute("SELECT COUNT(*) AS n FROM sale_items WHERE medicine_id=%s", (mid,))
            sold = cur.fetchone()['n']
            cur.execute("SELECT COUNT(*) AS n FROM purchase_items WHERE medicine_id=%s", (mid,))
            bought = cur.fetchone()['n']
            if sold or bought:
                blocked.append(mid)
        if blocked:
            flash('Undo is blocked: %d imported item(s) are already in use (sold or purchased, medicine #%s). '
                  'Undo is only possible before any sale or purchase uses the imported rows.'
                  % (len(blocked), blocked[0]), 'danger')
            return redirect(url_for('import_preview'))
        # no sale or purchase touched these items: their batches came from the import itself
        for mid in created_ids:
            cur.execute("DELETE FROM batches WHERE medicine_id=%s", (mid,))
            cur.execute("UPDATE medicines SET is_deleted=1 WHERE medicine_id=%s", (mid,))
        snapshot = _json.loads(batch['updated_snapshot'] or '{}')
        for mid, old in snapshot.items():
            sets = ', '.join(f'{k} = %s' for k in old)
            cur.execute(f"UPDATE medicines SET {sets} WHERE medicine_id=%s",
                        list(old.values()) + [int(mid)])
        cur.execute("UPDATE import_batches SET status='undone', undone_at=NOW() WHERE batch_id=%s", (batch_id,))
        audit(cur, 'products.import_undo', 'import', batch_id,
              f"{batch['filename'][:60]}: {len(created_ids)} created item(s) removed, {len(snapshot)} update(s) restored")
        mysql.connection.commit()
        flash('Import undone: new items were removed and updated items were restored.', 'success')
        return redirect(url_for('import_preview'))
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('import undo failed')
        flash_unexpected('Undo failed. Nothing was changed.')
        return redirect(url_for('import_preview'))
    finally:
        cur.close()


@app.route('/products/<key>/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_add(key):
    if key not in PS.SECTION_KEYS:
        return redirect(url_for('products_hub'))
    name = (request.form.get('name') or '').strip()[:100]
    strength = (request.form.get('strength') or '').strip()[:60] or None
    form = (request.form.get('dosage_form') or '').strip()
    try:
        price = round(float(request.form.get('price') or 0), 2)
    except ValueError:
        price = -1
    if not 2 <= len(name) <= 100:
        flash('Name must be 2 to 100 characters.', 'danger')
        return _back(key)
    if form not in PS.FORM_CHOICES[key] or PS.section_for(form) != key:
        flash('Choose a dosage form for this section.', 'danger')
        return _back(key)
    if price < 0:
        flash('Price must be a number, 0 or more.', 'danger')
        return _back(key)
    cur = mysql.connection.cursor()
    try:
        if repo.find_same_product(cur, name, strength):      # v86.54: same name + strength is an error
            flash(repo.duplicate_message(name, strength), 'danger')
            return _back(key)
        cid = DC._category_id(cur, PS.SECTION_CATEGORY[key])
        cur.execute("""INSERT INTO medicines (name, category_id, price, cost_price, stock_quantity, reorder_level, strength, dosage_form)
                       VALUES (%s,%s,%s,0,0,0,%s,%s)""", (name, cid, price, strength, form))
        audit(cur, 'products.add', 'medicine', cur.lastrowid, f"{name} ({form})")
        mysql.connection.commit()
        flash(f'Added {name}. Add stock by Purchase before selling.', 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('products add failed')
        flash_unexpected('The product could not be added.')
    finally:
        cur.close()
    return _back(key)


@app.route('/products/item/<int:mid>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_edit(mid):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM medicines WHERE medicine_id=%s", (mid,))
        med = cur.fetchone()
        if not med:
            flash('Product not found.', 'warning')
            return redirect(url_for('products_hub'))
        if request.method == 'POST':
            name = (request.form.get('name') or '').strip()[:100]
            strength = (request.form.get('strength') or '').strip()[:60] or None
            form = (request.form.get('dosage_form') or '').strip()
            barcode = re.sub(r'\D', '', request.form.get('barcode') or '')[:64] or None
            try:
                price = round(float(request.form.get('price') or 0), 2)
                reorder = int(request.form.get('reorder_level') or 0)
            except ValueError:
                flash('Price and reorder level must be numbers.', 'danger')
                return redirect(url_for('products_edit', mid=mid))
            if not 2 <= len(name) <= 100:
                flash('Name must be 2 to 100 characters.', 'danger')
                return redirect(url_for('products_edit', mid=mid))
            if repo.find_same_product(cur, name, strength, exclude_id=mid):   # v86.54
                flash(repo.duplicate_message(name, strength), 'danger')
                return redirect(url_for('products_edit', mid=mid))
            if form not in _forms():
                flash('Choose a valid dosage form.', 'danger')
                return redirect(url_for('products_edit', mid=mid))
            if price < 0 or reorder < 0:
                flash('Price and reorder level cannot be negative.', 'danger')
                return redirect(url_for('products_edit', mid=mid))
            if barcode:
                cur.execute("SELECT medicine_id FROM medicines WHERE barcode=%s AND medicine_id<>%s", (barcode, mid))
                if cur.fetchone():
                    flash('Another product already has this barcode.', 'danger')
                    return redirect(url_for('products_edit', mid=mid))
            schedule = (request.form.get('schedule') or '').strip()[:20] or None   # v87.08: controlled-drug schedule
            upp_raw = (request.form.get('units_per_pack') or '').strip()   # Stage 4: pack selling
            if upp_raw == '':
                units_per_pack = None
            elif upp_raw.isdigit() and 1 <= int(upp_raw) <= 10000:
                units_per_pack = int(upp_raw)
            else:
                flash('Units per pack must be a whole number between 1 and 10000, or left empty.', 'danger')
                return redirect(url_for('products_edit', mid=mid))
            cur.execute("""UPDATE medicines SET name=%s, strength=%s, dosage_form=%s, price=%s, reorder_level=%s, barcode=%s,
                           schedule=%s, units_per_pack=%s WHERE medicine_id=%s""",
                        (name, strength, form, price, reorder, barcode, schedule, units_per_pack, mid))
            audit(cur, 'products.edit', 'medicine', mid, f"{med['name']} -> {name} ({form}), schedule {schedule or 'none'}")
            mysql.connection.commit()
            flash('Product saved.', 'success')
            return redirect(url_for('products_section', key=PS.section_for(form)))
        cur.execute("""SELECT batch_number, expiry_date, quantity, purchase_price FROM batches
                       WHERE medicine_id=%s ORDER BY expiry_date""", (mid,))
        batches = cur.fetchall()
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('products edit failed')
        flash_unexpected('The product could not be saved.')
        return redirect(url_for('products_hub'))
    finally:
        cur.close()
    return render_template('products_edit.html', med=med, forms=_forms(), section=PS.section_for(med.get('dosage_form')),
                           batches=batches, batch_total=sum(int(b['quantity'] or 0) for b in batches))


@app.route('/products/<key>/clear-unused', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_clear_unused(key):
    """Removes every item of one section that has no sale, stock or drip history. Items with history stay."""
    if key not in PS.SECTION_KEYS:
        return redirect(url_for('products_hub'))
    cur = mysql.connection.cursor()
    removed, kept = 0, 0
    try:
        for r in _section_rows(cur, key):
            if DC.remove_blocker(cur, r['medicine_id']):
                kept += 1
                continue
            cur.execute("DELETE FROM medicines WHERE medicine_id=%s", (r['medicine_id'],))
            removed += 1
        audit(cur, 'products.clear_unused', 'section', 0, f"{key}: removed {removed}, kept {kept}")
        mysql.connection.commit()
        flash(f"Removed {removed} unused items. {kept} items with sales or stock history were kept.", 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('products clear unused failed')
        flash_unexpected('Nothing was removed.')
    finally:
        cur.close()
    return _back(key)


@app.route('/products/item/<int:mid>/remove', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_remove(mid):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT name, dosage_form FROM medicines WHERE medicine_id=%s", (mid,))
        med = cur.fetchone()
        if not med:
            return redirect(url_for('products_hub'))
        key = PS.section_for(med.get('dosage_form'))
        MREPO.purge_medicine(cur, mid)               # v86.29: hidden, bills keep their rows
        audit(cur, 'products.remove', 'medicine', mid, med['name'])
        mysql.connection.commit()
        flash(f"Removed {med['name']}.", 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('products remove failed')
        flash_unexpected('The product could not be removed. Nothing changed.')
        return redirect(url_for('products_hub'))
    finally:
        cur.close()
    return _back(key)


@app.route('/products/<key>/export')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_export(key):
    """CSV of one section, same columns the list loader reads, so an export can be loaded again."""
    if key not in PS.SECTION_KEYS:
        return redirect(url_for('products_hub'))
    cur = mysql.connection.cursor()
    try:
        rows = _section_rows(cur, key)
    finally:
        cur.close()
    header = ['generic_name', 'strength', 'dosage_form', 'barcode', 'price', 'stock', 'reorder_level', 'next_expiry']
    wanted = {x for x in (request.args.get('ids') or '').split(',') if x.isdigit()}   # v86.36: Export Selected
    if wanted:
        rows = [r for r in rows if str(r['medicine_id']) in wanted]
    data = [[r['generic_name'] or r['name'], r['strength'] or '', r['dosage_form'] or '', r['barcode'] or '',
             r['price'] or 0, r['stock'], r['reorder_level'] or 0, r['next_expiry'] or ''] for r in rows]
    return _csv_response(header, data, f'medigen_{key}.csv')


@app.route('/products/item/<int:mid>/receive', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def products_receive(mid):
    """Stock in for one product: quantity, batch and expiry. Makes the item sellable."""
    cur = mysql.connection.cursor()
    try:
        try:
            qty = int(request.form.get('qty') or 0)
            cost = round(float(request.form.get('cost') or 0), 2)
            expiry = _date.fromisoformat(request.form.get('expiry') or '')
        except ValueError:
            flash('Quantity must be a number, cost a number and expiry a date.', 'danger')
            return redirect(request.referrer or url_for('products_hub'))
        batch = re.sub(r'[^A-Za-z0-9\-_/]', '', request.form.get('batch') or '')[:50] or f'OPEN-{_date.today():%Y%m%d}'
        if not 1 <= qty <= 100000:
            flash('Quantity must be between 1 and 100000.', 'danger')
            return redirect(request.referrer or url_for('products_hub'))
        if expiry <= _date.today():
            flash('Expiry date must be in the future.', 'danger')
            return redirect(request.referrer or url_for('products_hub'))
        med = repo.lock_medicine(cur, mid)
        if not med:
            flash('Product not found.', 'warning')
            return redirect(url_for('products_hub'))
        key = PS.section_for(med.get('dosage_form'))
        cur.execute("SELECT batch_id, expiry_date FROM batches WHERE medicine_id=%s AND batch_number=%s FOR UPDATE",
                    (mid, batch))
        b = cur.fetchone()
        if b:
            if str(b['expiry_date']) != str(expiry):
                flash(f'Batch {batch} already exists with expiry {b["expiry_date"]}. Use another batch number.', 'danger')
                return redirect(request.referrer or url_for('products_hub'))
            cur.execute("UPDATE batches SET quantity = quantity + %s, purchase_price = %s WHERE batch_id=%s",
                        (qty, cost, b['batch_id']))
        else:
            cur.execute("""INSERT INTO batches (medicine_id, batch_number, expiry_date, quantity, purchase_price)
                           VALUES (%s,%s,%s,%s,%s)""", (mid, batch, expiry, qty, cost))
        old = int(med['stock_quantity'] or 0)
        repo.set_stock(cur, mid, old + qty)
        repo.insert_adjustment(cur, mid, session['user_id'], qty, old, old + qty, 'Stock received', f'Batch {batch}')
        audit(cur, 'products.receive', 'medicine', mid, f"{med['name']}: +{qty} batch {batch} exp {expiry}")
        mysql.connection.commit()
        flash(f"{med['name']}: {qty} received. Stock now {old + qty}.", 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('products receive failed')
        flash_unexpected('Stock was not received. Nothing changed.')
        return redirect(url_for('products_hub'))
    finally:
        cur.close()
    return _back(key)
