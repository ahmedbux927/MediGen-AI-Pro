"""Routes: drug interaction pairs (v87.07). Staff add pairs; only an Admin deletes them.
A sale that contains a listed pair gets a warning after it is saved. Nothing is blocked."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import interactions as IX

VIEW_ROLES = ('Admin', 'Pharmacist')


def _medicine_id_by_name(cur, name):
    cur.execute("SELECT medicine_id FROM medicines WHERE LOWER(name) = LOWER(%s) AND is_deleted = 0", (name,))
    rows = cur.fetchall()
    if not rows:
        raise IX.InteractionError(f'Medicine not found: "{name}". Pick a name from the list.')
    if len(rows) > 1:
        raise IX.InteractionError(f'More than one medicine is named "{name}". Rename one of them first.')
    return rows[0]['medicine_id']


@app.route('/interactions')
@login_required
@role_required(*VIEW_ROLES)
@guarded
def interactions():
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT i.interaction_id, i.severity, i.note, i.created_at, a.name AS a_name, b.name AS b_name
                       FROM drug_interactions i
                       JOIN medicines a ON a.medicine_id = i.med_a_id
                       JOIN medicines b ON b.medicine_id = i.med_b_id
                       ORDER BY FIELD(i.severity, 'major', 'moderate', 'minor'), a.name, b.name""")
        rules = cur.fetchall()
        cur.execute("SELECT name FROM medicines WHERE is_deleted = 0 ORDER BY name LIMIT 3000")
        names = [r['name'] for r in cur.fetchall()]
    except Exception:
        app.logger.exception('interaction list failed')
        rules, names = [], []
        flash_unexpected('Could not load the interaction list.')
    finally:
        cur.close()
    return render_template('interactions.html', rules=rules, names=names, severities=IX.SEVERITIES,
                           is_admin=session.get('role') == 'Admin', shop=get_setting('shop_name'))


@app.route('/interactions/add', methods=['POST'])
@login_required
@role_required(*VIEW_ROLES)
@guarded
def interaction_add():
    first = (request.form.get('first') or '').strip()[:100]
    second = (request.form.get('second') or '').strip()[:100]
    note = (request.form.get('note') or '').strip()[:IX.NOTE_MAX] or None
    cur = mysql.connection.cursor()
    try:
        a = _medicine_id_by_name(cur, first)
        b = _medicine_id_by_name(cur, second)
        low, high = IX.normalise_pair(a, b)
        severity = IX.check_severity(request.form.get('severity', 'moderate'))
        cur.execute("SELECT interaction_id FROM drug_interactions WHERE med_a_id=%s AND med_b_id=%s", (low, high))
        if cur.fetchone():
            raise IX.InteractionError('This pair is already listed. Delete the old entry first to change it.')
        cur.execute("""INSERT INTO drug_interactions (med_a_id, med_b_id, severity, note, created_by)
                       VALUES (%s,%s,%s,%s,%s)""", (low, high, severity, note, session.get('user_id')))
        audit(cur, 'interaction.add', 'drug_interaction', cur.lastrowid, f'{first} + {second}: {severity}')
        mysql.connection.commit()
        flash(f'Pair saved: {first} with {second} ({severity}).', 'success')
    except IX.InteractionError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Could not save the pair. Nothing was changed.')
    finally:
        cur.close()
    return redirect(url_for('interactions'))


@app.route('/interactions/<int:interaction_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def interaction_delete(interaction_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT interaction_id FROM drug_interactions WHERE interaction_id=%s", (interaction_id,))
        if not cur.fetchone():
            raise IX.InteractionError('This pair was not found. It may already be deleted.')
        cur.execute("DELETE FROM drug_interactions WHERE interaction_id=%s", (interaction_id,))
        audit(cur, 'interaction.delete', 'drug_interaction', interaction_id, 'pair removed')
        mysql.connection.commit()
        flash('Pair deleted.', 'success')
    except IX.InteractionError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Could not delete the pair.')
    finally:
        cur.close()
    return redirect(url_for('interactions'))
