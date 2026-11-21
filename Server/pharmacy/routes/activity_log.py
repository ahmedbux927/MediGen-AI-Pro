"""Routes: Activity Log with filters (v86.49). Admin only, read only."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _valid_date
from pharmacy.repos import activity_log as repo


@app.route('/activity-log')
@login_required
@role_required('Admin')
@guarded
def activity_log():
    username = (request.args.get('user') or '').strip()[:50]
    action = (request.args.get('action') or '').strip()[:40]
    entity = (request.args.get('entity') or '').strip()[:40]
    date_from = _valid_date(request.args.get('from', ''))
    date_to = _valid_date(request.args.get('to', ''))
    cur = mysql.connection.cursor()
    rows = repo.find_entries(cur, username, action, entity, date_from, date_to)
    actions = repo.distinct_actions(cur)
    cur.close()
    return render_template('activity_log.html', rows=rows, actions=actions, f_user=username,
                           f_action=action, f_entity=entity, f_from=date_from, f_to=date_to,
                           limit=repo.LIMIT, shop=get_setting('shop_name'))
