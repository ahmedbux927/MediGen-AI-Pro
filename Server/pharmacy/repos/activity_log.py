"""SQL for the Activity Log filter page (v86.49). Read only: it only SELECTs from audit_log."""

LIMIT = 200


def _like(text):
    # escape LIKE wildcards so a typed % or _ is searched as plain text
    return '%' + text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def find_entries(cur, username='', action='', entity='', date_from='', date_to=''):
    sql = """SELECT audit_id, created_at, username, action, entity, entity_id, details
             FROM audit_log WHERE 1 = 1"""
    params = []
    if username:
        sql += " AND username LIKE %s"; params.append(_like(username))
    if action:
        sql += " AND action = %s"; params.append(action)
    if entity:
        sql += " AND entity = %s"; params.append(entity)
    if date_from:
        sql += " AND DATE(created_at) >= %s"; params.append(date_from)
    if date_to:
        sql += " AND DATE(created_at) <= %s"; params.append(date_to)
    sql += " ORDER BY audit_id DESC LIMIT %s"
    params.append(LIMIT)
    cur.execute(sql, params)
    return cur.fetchall()


def distinct_actions(cur):
    cur.execute("SELECT DISTINCT action FROM audit_log ORDER BY action LIMIT 300")
    return [r['action'] for r in cur.fetchall()]
