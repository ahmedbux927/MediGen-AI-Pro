"""Routes: controlled-drug register viewer and export (v87.02). Read only.
Entries are written automatically by the sale (pharmacy/services/sales.py) and cannot be edited or deleted.
Export asks the user to type their own password, the same safety step used for records clear."""
import bcrypt
from datetime import date
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _like
from pharmacy.services import controlled_register as CR

REG_ROLES = ('Admin', 'Pharmacist')
ROW_LIMIT = 500


def _filters(args):
    start, end = CR.parse_range(args.get('start', '').strip(), args.get('end', '').strip(), date.today())
    q = (args.get('q') or '').strip()[:60]
    schedule = (args.get('schedule') or '').strip()[:20]
    where, params = ["DATE(cr.created_at) BETWEEN %s AND %s"], [start, end]
    if q:
        where.append("m.name LIKE %s")
        params.append(_like(q))
    if schedule:
        where.append("cr.schedule = %s")
        params.append(schedule)
    return start, end, q, schedule, " WHERE " + " AND ".join(where), params


BASE_FROM = """FROM controlled_register cr
               JOIN medicines m ON m.medicine_id = cr.medicine_id
               LEFT JOIN batches b ON b.batch_id = cr.batch_id
               LEFT JOIN customers c ON c.customer_id = cr.customer_id
               LEFT JOIN users u ON u.user_id = cr.user_id"""


@app.route('/controlled-register')
@login_required
@role_required(*REG_ROLES)
@guarded
def controlled_register():
    try:
        start, end, q, schedule, wsql, params = _filters(request.args)
    except CR.RegisterError as e:
        flash(str(e), 'danger')
        start = end = date.today()
        q = schedule = ''
        wsql, params = " WHERE DATE(cr.created_at) = %s", [start]
    cur = mysql.connection.cursor()
    try:
        cur.execute(f"""SELECT cr.entry_id, cr.sale_id, cr.schedule, cr.quantity, cr.prescription_id, cr.created_at,
                               m.name AS medicine_name, b.batch_number, c.name AS customer_name, u.username
                        {BASE_FROM} {wsql} ORDER BY cr.created_at DESC, cr.entry_id DESC LIMIT %s""",
                    params + [ROW_LIMIT])
        entries = cur.fetchall()
        cur.execute(f"""SELECT m.name AS medicine_name, cr.schedule, cr.quantity {BASE_FROM} {wsql}""", params)
        summary = CR.summarise_entries(cur.fetchall())
        cur.execute("SELECT DISTINCT schedule FROM controlled_register ORDER BY schedule")
        schedules = [r['schedule'] for r in cur.fetchall()]
    except Exception:
        app.logger.exception('controlled register list failed')
        entries, summary, schedules = [], [], []
        flash_unexpected('Could not load the controlled register.')
    finally:
        cur.close()
    return render_template('controlled_register.html', entries=entries, summary=summary, schedules=schedules,
                           start=start, end=end, q=q, schedule=schedule, limit=ROW_LIMIT,
                           shop=get_setting('shop_name'))


@app.route('/controlled-register/export', methods=['POST'])
@login_required
@role_required(*REG_ROLES)
@guarded
def controlled_register_export():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        me = cur.fetchone()
        typed = request.form.get('password', '')
        if not me or not typed or not bcrypt.checkpw(typed.encode('utf-8'), me['password_hash'].encode('utf-8')):
            flash('Wrong password. Nothing was exported.', 'danger')
            return redirect(url_for('controlled_register', start=request.form.get('start', ''),
                                    end=request.form.get('end', ''), q=request.form.get('q', ''),
                                    schedule=request.form.get('schedule', '')))
        start, end, q, schedule, wsql, params = _filters(request.form)
        cur.execute(f"""SELECT cr.created_at, m.name AS medicine_name, cr.schedule, b.batch_number,
                               cr.quantity, c.name AS customer_name, cr.prescription_id, cr.sale_id, u.username
                        {BASE_FROM} {wsql} ORDER BY cr.created_at ASC, cr.entry_id ASC""", params)
        rows = cur.fetchall()
        audit(cur, 'controlled_register.export', 'controlled_register', None,
              f'{len(rows)} entries, {start} to {end}')
        mysql.connection.commit()
    except CR.RegisterError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('controlled_register'))
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Could not export the register.')
        return redirect(url_for('controlled_register'))
    finally:
        cur.close()
    header = ['Date and time', 'Medicine', 'Schedule', 'Batch', 'Quantity', 'Customer', 'Prescription ID',
              'Sale ID', 'Recorded by']
    data = [(r['created_at'], r['medicine_name'], r['schedule'], r['batch_number'] or '', r['quantity'],
             r['customer_name'] or '', r['prescription_id'] or '', r['sale_id'], r['username'] or '') for r in rows]
    return _csv_response(header, data, f'controlled_register_{start}_{end}.csv')
