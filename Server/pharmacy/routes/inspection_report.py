"""Routes: inspection report (Stage 3, item D). One Excel file for a date range:
controlled drug register + cold chain readings + expiry write-offs.
Read only. Export asks the user to type their own password (same as the controlled register export)."""
import bcrypt
from datetime import date, timedelta
from flask import Response
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.exports import build_xlsx
from pharmacy.routes.controlled_register import BASE_FROM
from pharmacy.services import controlled_register as CR
from pharmacy.services import inspection_export as IE

REPORT_ROLES = ('Admin', 'Pharmacist')
MAX_DAYS = 366
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _range(args):
    start, end = CR.parse_range((args.get('start') or '').strip(), (args.get('end') or '').strip(), date.today())
    if start > end:
        raise ValueError('The start date must be before the end date.')
    if (end - start) > timedelta(days=MAX_DAYS):
        raise ValueError(f'Please choose a range of {MAX_DAYS} days or less.')
    return start, end


@app.route('/inspection-report')
@login_required
@role_required(*REPORT_ROLES)
def inspection_report():
    today = date.today()
    return render_template('inspection_report.html', start=(today - timedelta(days=30)).isoformat(),
                           end=today.isoformat(), max_days=MAX_DAYS)


@app.route('/inspection-report/export', methods=['POST'])
@login_required
@role_required(*REPORT_ROLES)
@guarded
def inspection_report_export():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        me = cur.fetchone()
        typed = request.form.get('password', '')
        if not me or not typed or not bcrypt.checkpw(typed.encode('utf-8'), me['password_hash'].encode('utf-8')):
            flash('Wrong password. Nothing was exported.', 'danger')
            return redirect(url_for('inspection_report'))
        start, end = _range(request.form)
        cur.execute(f"""SELECT cr.created_at, m.name AS medicine_name, cr.schedule, b.batch_number, cr.quantity,
                               c.name AS customer_name, cr.sale_id, u.username
                        {BASE_FROM} WHERE DATE(cr.created_at) BETWEEN %s AND %s
                        ORDER BY cr.created_at ASC""", (start, end))
        controlled = cur.fetchall()
        cur.execute("""SELECT t.recorded_at, t.location, t.temperature_c, t.in_range, t.note, u.username
                       FROM temperature_logs t LEFT JOIN users u ON u.user_id = t.user_id
                       WHERE DATE(t.recorded_at) BETWEEN %s AND %s ORDER BY t.recorded_at ASC""", (start, end))
        cold = cur.fetchall()
        cur.execute("""SELECT sa.created_at, m.name AS medicine_name, sa.change_qty, sa.note, u.username
                       FROM stock_adjustments sa JOIN medicines m ON m.medicine_id = sa.medicine_id
                       LEFT JOIN users u ON u.user_id = sa.user_id
                       WHERE sa.reason = 'Expired' AND DATE(sa.created_at) BETWEEN %s AND %s
                       ORDER BY sa.created_at ASC""", (start, end))
        writeoffs = cur.fetchall()
        table = IE.merge(controlled, cold, writeoffs)
        audit(cur, 'inspection_report.export', 'inspection_report', None,
              f'{len(table)} rows, {start} to {end}')
        mysql.connection.commit()
    except ValueError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('inspection_report'))
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('inspection report export failed')
        flash_unexpected('Could not create the inspection report.')
        return redirect(url_for('inspection_report'))
    finally:
        cur.close()
    summary = [('Period', f'{start} to {end}'),
               ('Controlled drug entries', len(controlled)),
               ('Cold chain readings', len(cold)),
               ('Out-of-range readings', sum(1 for r in cold if not r.get('in_range'))),
               ('Expiry write-offs', len(writeoffs))]
    notes = ['Generated from MediGen AI Pro. Entries are read only.']
    data = build_xlsx('Inspection report', IE.HEADERS, table, summary=summary, notes=notes)
    return Response(data, mimetype=XLSX_MIME,
                    headers={'Content-Disposition': f'attachment; filename=inspection_report_{start}_{end}.xlsx'})
