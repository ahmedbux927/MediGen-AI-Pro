"""Routes: cold chain temperature log (v87.01). Any shop role can record a reading. Readings are kept as a permanent record.
Rules (range, parsing, saving) live in pharmacy/services/temperature.py."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import temperature as TP

COLD_ROLES = ('Admin', 'Pharmacist', 'Cashier')


@app.route('/cold-chain')
@login_required
@role_required(*COLD_ROLES)
@guarded
def cold_chain():
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT t.log_id, t.location, t.temperature_c, t.in_range, t.note, t.recorded_at,
                              u.username AS recorded_name
                       FROM temperature_logs t LEFT JOIN users u ON u.user_id = t.user_id
                       ORDER BY t.recorded_at DESC, t.log_id DESC LIMIT 60""")
        logs = cur.fetchall()
        cur.execute("""SELECT t.log_id, t.location, t.temperature_c, t.in_range, t.recorded_at
                       FROM temperature_logs t
                       JOIN (SELECT location, MAX(log_id) AS last_id FROM temperature_logs GROUP BY location) x
                         ON x.last_id = t.log_id
                       ORDER BY t.location""")
        latest = cur.fetchall()
        cur.execute("""SELECT location, COUNT(*) AS readings, SUM(in_range = 0) AS outside
                       FROM temperature_logs WHERE DATE(recorded_at) = CURDATE()
                       GROUP BY location ORDER BY location""")
        today = [dict(r, outside=int(r['outside'] or 0)) for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT location FROM temperature_logs ORDER BY location LIMIT 50")
        known = [r['location'] for r in cur.fetchall()]
    except Exception:
        app.logger.exception('cold chain list failed')
        logs, latest, today, known = [], [], [], []
        flash_unexpected('Could not load the cold chain log.')
    finally:
        cur.close()
    if not known:
        known = ['Fridge 1']
    return render_template('cold_chain.html', logs=logs, latest=latest, today=today, known=known,
                           low=TP.DEFAULT_MIN_C, high=TP.DEFAULT_MAX_C, shop=get_setting('shop_name'))


@app.route('/cold-chain/record', methods=['POST'])
@login_required
@role_required(*COLD_ROLES)
@guarded
def cold_chain_record():
    location = (request.form.get('location') or '').strip()
    temperature = request.form.get('temperature') or ''
    note = (request.form.get('note') or '').strip()[:200]
    cur = mysql.connection.cursor()
    try:
        result = TP.record_reading(cur, location, temperature, session['user_id'], note)
        state = 'in range' if result['in_range'] else 'OUT OF RANGE'
        audit(cur, 'cold_chain.record', 'temperature_log', result['log_id'],
              f"{location.strip()[:40]}: {result['temperature']} C ({state})")
        mysql.connection.commit()
        if result['in_range']:
            flash(f"Saved: {location} at {result['temperature']} C, within the 2 to 8 C range.", 'success')
        else:
            flash(f"Saved: {location} at {result['temperature']} C is outside the 2 to 8 C range. "
                  "Check the fridge and note what you did in the note box.", 'warning')
    except TP.TemperatureError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong. The reading was not saved.')
    finally:
        cur.close()
    return redirect(url_for('cold_chain'))
