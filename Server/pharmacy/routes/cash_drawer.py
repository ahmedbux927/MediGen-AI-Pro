"""Routes: cash drawer (v86.60). Open the drawer, record cash in and out, close with a count and see shortage."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.repos import cash_drawer as repo
from pharmacy.services import cash_drawer as CD

ROLES = ('Admin', 'Pharmacist', 'Cashier')


def _money(text):
    try:
        value = round(float(str(text or '').strip()), 2)
    except ValueError:
        return None
    return value if value == value and value >= 0 and value < 100000000 else None   # not NaN, not negative


def _state(cur, sess):
    since = sess['opened_at']
    cash_sales = repo.cash_sales_since(cur, since)
    refunds = repo.cash_refunds_since(cur, since)
    cin, cout = repo.movement_totals(cur, sess['session_id'])
    opening = float(sess['opening_amount'] or 0)
    expected = CD.expected_cash(opening, cash_sales, refunds, cin, cout)
    return {'opening': opening, 'cash_sales': cash_sales, 'refunds': refunds,
            'cash_in': cin, 'cash_out': cout, 'expected': expected}


@app.route('/cash')
@login_required
@role_required(*ROLES)
@guarded
def cash_drawer():
    cur = mysql.connection.cursor()
    sess = repo.open_session(cur)
    state = _state(cur, sess) if sess else None
    moves = repo.movements(cur, sess['session_id']) if sess else []
    hist = repo.history(cur)
    cur.close()
    return render_template('cash_drawer.html', sess=sess, state=state, moves=moves, hist=hist,
                           shop=get_setting('shop_name'))


@app.route('/cash/open', methods=['POST'])
@login_required
@role_required(*ROLES)
@guarded
def cash_open():
    amount = _money(request.form.get('opening'))
    if amount is None:
        flash('Opening cash must be a valid amount (0 or more).', 'warning')
        return redirect(url_for('cash_drawer'))
    cur = mysql.connection.cursor()
    try:
        if repo.open_session(cur):
            flash('The drawer is already open.', 'warning')
            return redirect(url_for('cash_drawer'))
        sid = repo.insert_session(cur, amount, session.get('user_id'))
        audit(cur, 'cash.open', 'cash_session', sid, f'Opening cash Rs. {amount:,.2f}')
        mysql.connection.commit()
        flash(f'Drawer opened. Opening cash Rs. {amount:,.2f}.', 'success')
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
    return redirect(url_for('cash_drawer'))


@app.route('/cash/movement', methods=['POST'])
@login_required
@role_required(*ROLES)
@guarded
def cash_movement():
    kind = request.form.get('kind')
    amount = _money(request.form.get('amount'))
    reason = (request.form.get('reason') or '').strip()[:255]
    if kind not in ('in', 'out') or not amount or amount <= 0:
        flash('Amount must be more than 0.', 'warning')
        return redirect(url_for('cash_drawer'))
    if not reason:
        flash('A reason is required (for example: tea, electricity, credit repaid).', 'warning')
        return redirect(url_for('cash_drawer'))
    cur = mysql.connection.cursor()
    try:
        sess = repo.open_session(cur)
        if not sess:
            flash('Please open the drawer first.', 'warning')
            return redirect(url_for('cash_drawer'))
        repo.insert_movement(cur, sess['session_id'], kind, amount, reason, session.get('user_id'))
        audit(cur, 'cash.in' if kind == 'in' else 'cash.out', 'cash_session', sess['session_id'],
              f'Rs. {amount:,.2f}: {reason}')
        mysql.connection.commit()
        flash(f"Cash {'in' if kind == 'in' else 'out'} saved: Rs. {amount:,.2f}.", 'success')
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
    return redirect(url_for('cash_drawer'))


@app.route('/cash/close', methods=['POST'])
@login_required
@role_required(*ROLES)
@guarded
def cash_close():
    counted = _money(request.form.get('counted'))
    note = (request.form.get('note') or '').strip()[:255] or None
    if counted is None:
        flash('The counted cash must be a valid amount.', 'warning')
        return redirect(url_for('cash_drawer'))
    cur = mysql.connection.cursor()
    try:
        sess = repo.open_session(cur)
        if not sess:
            flash('The drawer is already closed.', 'warning')
            return redirect(url_for('cash_drawer'))
        state = _state(cur, sess)
        diff = CD.shortage(counted, state['expected'])
        repo.close_session(cur, sess['session_id'], counted, state['expected'], diff, session.get('user_id'), note)
        audit(cur, 'cash.close', 'cash_session', sess['session_id'],
              f"Expected Rs. {state['expected']:,.2f}, counted Rs. {counted:,.2f}, diff Rs. {diff:,.2f}")
        mysql.connection.commit()
        kind, text = CD.describe(diff)
        flash(f'Drawer closed. Expected Rs. {state["expected"]:,.0f}, counted Rs. {counted:,.0f}. {text}',
              'danger' if kind == 'short' else ('warning' if kind == 'extra' else 'success'))
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
    return redirect(url_for('cash_drawer'))
