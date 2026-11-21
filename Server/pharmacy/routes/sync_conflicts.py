"""Routes: Stock conflicts from phone sync (v87.22). Admin only.

A phone bill sold more than the server's stock while the phone was offline. The bill is saved;
the Admin checks the shelf here and marks the row as checked."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403


@app.route('/sync-conflicts')
@login_required
@role_required('Admin')
@guarded
def sync_conflicts_page():
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT conflict_id, created_at, medicine_name, requested, stock_before, client_uuid,
                              sale_id, resolved, resolved_at, resolve_note
                       FROM sync_conflicts ORDER BY resolved ASC, created_at DESC LIMIT 300""")
        rows = cur.fetchall()
    finally:
        cur.close()
    open_count = sum(1 for r in rows if not r['resolved'])
    return render_template('sync_conflicts.html', rows=rows, open_count=open_count, shop=get_setting('shop_name'))


@app.route('/sync-conflicts/<int:conflict_id>/resolve', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def sync_conflict_resolve(conflict_id):
    note = (request.form.get('note') or '').strip()[:255] or 'Checked on the shelf'
    cur = mysql.connection.cursor()
    try:
        cur.execute("""UPDATE sync_conflicts SET resolved = 1, resolved_at = NOW(), resolved_by = %s, resolve_note = %s
                       WHERE conflict_id = %s AND resolved = 0""", (session.get('user_id'), note, conflict_id))
        if cur.rowcount:
            audit(cur, 'sync.conflict_checked', 'sync_conflict', conflict_id, note)
        mysql.connection.commit()
    finally:
        cur.close()
    flash('Marked as checked.', 'success')
    return redirect(url_for('sync_conflicts_page'))
