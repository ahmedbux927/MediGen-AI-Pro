"""Routes: stock count (v87.00). Admin and Pharmacist count shelves; only an Admin approves the result.
All rules live in pharmacy/services/stock_count.py; these routes only read the form and show messages."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import stock_count as SC

COUNT_ROLES = ('Admin', 'Pharmacist')
MAX_SAVE_LINES = 2000


def _lines(cur, count_id):
    cur.execute("""SELECT l.medicine_id, l.system_qty, l.counted_qty, m.name, m.barcode, m.dosage_form,
                          m.stock_quantity AS current_qty
                   FROM stock_count_lines l JOIN medicines m ON m.medicine_id = l.medicine_id
                   WHERE l.count_id = %s ORDER BY m.name ASC""", (count_id,))
    return cur.fetchall()


def _cost_map(cur):
    cur.execute("SELECT medicine_id, MAX(IFNULL(purchase_price, 0)) AS cost FROM batches WHERE quantity > 0 GROUP BY medicine_id")
    return {r['medicine_id']: float(r['cost'] or 0) for r in cur.fetchall()}


def _act(count_id, work, success, audit_action):
    """Run one state change in a transaction and go back to the count page."""
    cur = mysql.connection.cursor()
    try:
        work(cur)
        audit(cur, audit_action, 'stock_count', count_id, success)
        mysql.connection.commit()
        flash(success, 'success')
    except SC.CountError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('stock_count_detail', count_id=count_id))


@app.route('/stock-count')
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_home():
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT c.count_id, c.status, c.note, c.started_at, c.submitted_at, c.approved_at,
                              su.username AS started_name, au.username AS approved_name,
                              (SELECT COUNT(*) FROM stock_count_lines l WHERE l.count_id = c.count_id) AS line_total,
                              (SELECT COUNT(*) FROM stock_count_lines l
                               WHERE l.count_id = c.count_id AND l.counted_qty IS NOT NULL) AS counted_total
                       FROM stock_counts c
                       LEFT JOIN users su ON su.user_id = c.started_by
                       LEFT JOIN users au ON au.user_id = c.approved_by
                       ORDER BY c.count_id DESC LIMIT 30""")
        counts = cur.fetchall()
    except Exception:
        app.logger.exception('stock count list failed')
        counts = []
        flash_unexpected('Could not load stock counts.')
    finally:
        cur.close()
    open_count = next((c for c in counts if c['status'] in ('open', 'submitted')), None)
    return render_template('stock_count.html', counts=counts, open_count=open_count,
                           is_admin=session.get('role') == 'Admin', shop=get_setting('shop_name'))


@app.route('/stock-count/start', methods=['POST'])
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_start():
    note = (request.form.get('note') or '').strip()[:255]
    cur = mysql.connection.cursor()
    try:
        count_id = SC.start_count(cur, session['user_id'], note)
        audit(cur, 'stock_count.start', 'stock_count', count_id, 'Stock count started')
        mysql.connection.commit()
        flash('Stock count started. Enter the counted quantity for each medicine, then save.', 'success')
        return redirect(url_for('stock_count_detail', count_id=count_id))
    except SC.CountError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    finally:
        cur.close()
    return redirect(url_for('stock_count_home'))


@app.route('/stock-count/<int:count_id>')
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_detail(count_id):
    q = (request.args.get('q') or '').strip()[:60].lower()
    view = request.args.get('view', 'all')
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT c.*, su.username AS started_name, au.username AS approved_name
                       FROM stock_counts c
                       LEFT JOIN users su ON su.user_id = c.started_by
                       LEFT JOIN users au ON au.user_id = c.approved_by
                       WHERE c.count_id = %s""", (count_id,))
        count = cur.fetchone()
        if not count:
            flash('Stock count not found.', 'danger')
            return redirect(url_for('stock_count_home'))
        lines = _lines(cur, count_id)
        costs = _cost_map(cur)
    finally:
        cur.close()

    clash = SC.conflicts(lines, {l['medicine_id']: l['current_qty'] or 0 for l in lines}) if count['status'] == 'submitted' else []
    summary = SC.summarise(lines, costs)
    rows = []
    for l in lines:
        counted = l['counted_qty'] is not None
        diff = SC.variance(l['system_qty'], l['counted_qty']) if counted else None
        row = dict(l, diff=diff, counted=counted)
        if q and q not in (l['name'] or '').lower() and q not in (l['barcode'] or '').lower():
            continue
        if view == 'todo' and counted:
            continue
        if view == 'changed' and not (counted and diff):
            continue
        rows.append(row)
    if view not in ('all', 'todo', 'changed'):
        view = 'all'
    return render_template('stock_count_detail.html', count=count, rows=rows, summary=summary,
                           clash=len(clash), q=q, view=view, is_admin=session.get('role') == 'Admin',
                           editable=count['status'] == 'open', shop=get_setting('shop_name'))


@app.route('/stock-count/<int:count_id>/save', methods=['POST'])
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_save(count_id):
    ids = request.form.getlist('medicine_id')[:MAX_SAVE_LINES]
    qtys = request.form.getlist('counted_qty')[:MAX_SAVE_LINES]
    cur = mysql.connection.cursor()
    try:
        saved = 0
        for mid, raw in zip(ids, qtys):
            raw = (raw or '').strip()
            if raw == '':
                continue                      # empty box: leave this medicine as it was
            try:
                mid_int = int(mid)
            except (TypeError, ValueError):
                raise SC.CountError('A medicine id on the form is not valid. Reload the page and try again.')
            SC.record_count(cur, count_id, mid_int, raw, session['user_id'])
            saved += 1
        if saved:
            audit(cur, 'stock_count.save', 'stock_count', count_id, f'{saved} count line(s) saved')
        mysql.connection.commit()
        flash(f'{saved} count line(s) saved.' if saved else 'Nothing to save. Enter at least one counted quantity.',
              'success' if saved else 'warning')
    except SC.CountError as e:
        mysql.connection.rollback()
        flash(str(e) + ' Nothing was saved.', 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong. Nothing was saved.')
    finally:
        cur.close()
    return redirect(url_for('stock_count_detail', count_id=count_id, q=request.form.get('q', ''),
                            view=request.form.get('view', 'all')))


@app.route('/stock-count/<int:count_id>/submit', methods=['POST'])
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_submit(count_id):
    return _act(count_id, lambda cur: SC.submit_count(cur, count_id),
                'Count submitted. An Admin can now approve it.', 'stock_count.submit')


@app.route('/stock-count/<int:count_id>/reopen', methods=['POST'])
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_reopen(count_id):
    return _act(count_id, lambda cur: SC.reopen_count(cur, count_id),
                'Count sent back to counting.', 'stock_count.reopen')


@app.route('/stock-count/<int:count_id>/cancel', methods=['POST'])
@login_required
@role_required(*COUNT_ROLES)
@guarded
def stock_count_cancel(count_id):
    return _act(count_id, lambda cur: SC.cancel_count(cur, count_id),
                'Count cancelled. Stock was not changed.', 'stock_count.cancel')


@app.route('/stock-count/<int:count_id>/approve', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def stock_count_approve(count_id):
    result = {}

    def work(cur):
        result['changed'] = SC.approve_count(cur, count_id, session['user_id'], session.get('role'), audit)
    return _act(count_id, work, 'Count approved. Stock was updated for the changed medicines.',
                'stock_count.approve')
