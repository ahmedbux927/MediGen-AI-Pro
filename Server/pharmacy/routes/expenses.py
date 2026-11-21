"""Routes: shop expenses (v86.61). Cash paid from the drawer is also written as a cash out, so the drawer stays right."""
from datetime import date
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _valid_date
from pharmacy.repos import expenses as repo
from pharmacy.repos import cash_drawer as CDR
from pharmacy.services.cash_drawer import lock_message as cash_lock_message   # v87.03


def _month_bounds(text):
    try:
        first = datetime.strptime(text, '%Y-%m').date().replace(day=1)
    except (ValueError, TypeError):
        first = date.today().replace(day=1)
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, nxt - timedelta(days=1)


@app.route('/expenses')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def expenses():
    month = request.args.get('month', '') or date.today().strftime('%Y-%m')
    first, last = _month_bounds(month)
    cur = mysql.connection.cursor()
    rows = repo.list_for_month(cur, first.isoformat(), last.isoformat())
    total = repo.total_between(cur, first.isoformat(), last.isoformat())
    cats = repo.by_category(cur, first.isoformat(), last.isoformat())
    drawer_open = CDR.open_session(cur) is not None
    cur.close()
    return render_template('expenses.html', rows=rows, total=total, cats=cats, month=first.strftime('%Y-%m'),
                           categories=repo.CATEGORIES, paid_via=repo.PAID_VIA, today=date.today().isoformat(),
                           drawer_open=drawer_open, shop=get_setting('shop_name'))


@app.route('/expenses/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def expense_add():
    when = _valid_date(request.form.get('expense_date', ''))
    category = request.form.get('category', '')
    paid_via = request.form.get('paid_via', 'Cash')
    note = (request.form.get('note') or '').strip()[:255] or None
    try:
        amount = round(float(request.form.get('amount', '')), 2)
    except ValueError:
        amount = 0
    if not when or when > date.today().isoformat():
        flash('Invalid date. Enter today or an earlier date.', 'warning')
        return redirect(url_for('expenses'))
    if category not in repo.CATEGORIES or paid_via not in repo.PAID_VIA or not (0 < amount < 100000000):
        flash('Select a valid category, enter an amount above 0 and choose a payment method.', 'warning')
        return redirect(url_for('expenses'))
    cur = mysql.connection.cursor()
    try:
        lock = cash_lock_message(CDR.open_session(cur) is not None, paid_via, amount, 'before recording this cash expense')
        if lock:                                  # v87.03: nothing is written when the drawer is closed
            mysql.connection.rollback()
            flash(lock, 'warning')
            return redirect(url_for('expenses'))
        eid = repo.insert(cur, when, category, amount, paid_via, note, session.get('user_id'))
        drawer_note = ''
        if paid_via == 'Cash':
            sess = CDR.open_session(cur)
            if sess:
                CDR.insert_movement(cur, sess['session_id'], 'out', amount, f'Expense: {category}' + (f' ({note})' if note else ''),
                                    session.get('user_id'))
                drawer_note = ' A cash out entry was also added to the drawer.'
        audit(cur, 'expense.add', 'expense', eid, f'{category} Rs. {amount:,.2f} ({paid_via})')
        mysql.connection.commit()
        flash(f'Expense saved: Rs. {amount:,.2f}.{drawer_note}', 'success')
    except Exception:
        mysql.connection.rollback()
        raise
    finally:
        cur.close()
    return redirect(url_for('expenses'))
