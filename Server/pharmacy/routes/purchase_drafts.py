"""Routes: purchase drafts (v87.05). Suggested orders for review, CSV export and marking as sent.
Drafts never change stock. Receive the goods on the Purchase page as before."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _csv_response
from pharmacy.routes.purchase_suggest import _suggestion_rows
from pharmacy.services import purchase_drafts as PD

DRAFT_ROLES = ('Admin', 'Pharmacist')


def _draft(cur, draft_id):
    cur.execute("""SELECT d.*, s.name AS supplier_name, u.username AS created_name
                   FROM purchase_drafts d LEFT JOIN suppliers s ON s.supplier_id = d.supplier_id
                   LEFT JOIN users u ON u.user_id = d.created_by WHERE d.draft_id = %s""", (draft_id,))
    return cur.fetchone()


def _lines(cur, draft_id):
    cur.execute("""SELECT l.medicine_id, l.quantity, l.unit_cost, m.name, m.barcode, m.dosage_form, m.stock_quantity
                   FROM purchase_draft_lines l JOIN medicines m ON m.medicine_id = l.medicine_id
                   WHERE l.draft_id = %s ORDER BY m.name ASC""", (draft_id,))
    return cur.fetchall()


@app.route('/purchase/drafts')
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_drafts():
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT d.draft_id, d.status, d.created_at, d.sent_at, s.name AS supplier_name,
                              (SELECT COUNT(*) FROM purchase_draft_lines l WHERE l.draft_id = d.draft_id) AS line_count,
                              (SELECT IFNULL(SUM(l.quantity * l.unit_cost), 0) FROM purchase_draft_lines l
                               WHERE l.draft_id = d.draft_id) AS total
                       FROM purchase_drafts d LEFT JOIN suppliers s ON s.supplier_id = d.supplier_id
                       ORDER BY FIELD(d.status, 'draft', 'sent', 'cancelled'), d.draft_id DESC LIMIT 100""")
        drafts = cur.fetchall()
        suggestions = len(_suggestion_rows(cur))
    except Exception:
        app.logger.exception('purchase drafts list failed')
        drafts, suggestions = [], 0
        flash_unexpected('Could not load purchase drafts.')
    finally:
        cur.close()
    return render_template('purchase_drafts.html', drafts=drafts, suggestions=suggestions,
                           shop=get_setting('shop_name'))


@app.route('/purchase/drafts/create', methods=['POST'])
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_drafts_create():
    cur = mysql.connection.cursor()
    try:
        rows = _suggestion_rows(cur)
        drafts, lines = PD.create_from_suggestions(cur, session['user_id'], rows)
        if drafts:
            audit(cur, 'purchase_draft.create', 'purchase_draft', None, f'{drafts} draft(s), {lines} line(s)')
        mysql.connection.commit()
        if drafts:
            flash(f'{drafts} draft order(s) created with {lines} item(s). Stock was not changed.', 'success')
        else:
            flash('Nothing new to order. Items already on an open draft are not added again.', 'info')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Could not create drafts. Nothing was saved.')
    finally:
        cur.close()
    return redirect(url_for('purchase_drafts'))


@app.route('/purchase/drafts/<int:draft_id>')
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_draft_detail(draft_id):
    cur = mysql.connection.cursor()
    try:
        draft = _draft(cur, draft_id)
        if not draft:
            flash('Draft not found.', 'danger')
            return redirect(url_for('purchase_drafts'))
        lines = _lines(cur, draft_id)
    finally:
        cur.close()
    total = PD.lines_total(lines)
    return render_template('purchase_draft.html', draft=draft, lines=lines, total=total,
                           editable=draft['status'] == 'draft', max_qty=PD.MAX_QTY, shop=get_setting('shop_name'))


@app.route('/purchase/drafts/<int:draft_id>/save', methods=['POST'])
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_draft_save(draft_id):
    ids = request.form.getlist('medicine_id')[:2000]
    qtys = request.form.getlist('quantity')[:2000]
    cur = mysql.connection.cursor()
    try:
        draft = _draft(cur, draft_id)
        if not draft or draft['status'] != 'draft':
            raise PD.DraftError('Only an open draft can be changed.')
        pairs = []
        for mid, raw in zip(ids, qtys):
            try:
                mid_int = int(mid)
            except (TypeError, ValueError):
                raise PD.DraftError('A medicine id on the form is not valid. Reload the page and try again.')
            pairs.append((mid_int, PD.parse_qty(raw)))
        PD.apply_quantities(cur, draft_id, pairs)
        audit(cur, 'purchase_draft.edit', 'purchase_draft', draft_id, f'{len(pairs)} line(s) reviewed')
        mysql.connection.commit()
        flash('Draft saved.', 'success')
    except PD.DraftError as e:
        mysql.connection.rollback()
        flash(str(e) + ' Nothing was saved.', 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong. Nothing was saved.')
    finally:
        cur.close()
    return redirect(url_for('purchase_draft_detail', draft_id=draft_id))


def _change_status(draft_id, new_status, allowed_from, action, success):
    cur = mysql.connection.cursor()
    try:
        draft = _draft(cur, draft_id)
        if not draft or draft['status'] != allowed_from:
            raise PD.DraftError(f'This draft cannot be {action}.')
        if new_status == 'sent':
            cur.execute("UPDATE purchase_drafts SET status='sent', sent_at=NOW() WHERE draft_id=%s", (draft_id,))
        else:
            cur.execute("UPDATE purchase_drafts SET status=%s WHERE draft_id=%s", (new_status, draft_id))
        audit(cur, f'purchase_draft.{new_status}', 'purchase_draft', draft_id, success)
        mysql.connection.commit()
        flash(success, 'success')
    except PD.DraftError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('purchase_draft_detail', draft_id=draft_id))


@app.route('/purchase/drafts/<int:draft_id>/sent', methods=['POST'])
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_draft_sent(draft_id):
    return _change_status(draft_id, 'sent', 'draft', 'marked as sent',
                          'Draft marked as sent. Receive the goods on the Purchase page when they arrive.')


@app.route('/purchase/drafts/<int:draft_id>/cancel', methods=['POST'])
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_draft_cancel(draft_id):
    return _change_status(draft_id, 'cancelled', 'draft', 'cancelled', 'Draft cancelled.')


@app.route('/purchase/drafts/<int:draft_id>/export')
@login_required
@role_required(*DRAFT_ROLES)
@guarded
def purchase_draft_export(draft_id):
    cur = mysql.connection.cursor()
    try:
        draft = _draft(cur, draft_id)
        if not draft:
            flash('Draft not found.', 'danger')
            return redirect(url_for('purchase_drafts'))
        lines = _lines(cur, draft_id)
    finally:
        cur.close()
    data = [(draft['supplier_name'] or 'No supplier yet', l['name'], l['barcode'] or '', l['quantity'],
             l['unit_cost'], round(float(l['quantity']) * float(l['unit_cost'] or 0), 2)) for l in lines]
    return _csv_response(['Supplier', 'Medicine', 'Barcode', 'Quantity', 'Unit cost (Rs.)', 'Line total (Rs.)'],
                         data, f'purchase_draft_{draft_id}.csv')
