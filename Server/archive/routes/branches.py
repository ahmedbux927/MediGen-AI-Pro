"""Routes: multi-branch summary page (v87.11). Admin only: the token is a secret. Read-only."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import branch_view as BV

KEYS = ('branch_name', 'branch_url', 'branch_token')


def _settings(cur):
    cur.execute("SELECT setting_key, setting_value FROM app_settings WHERE setting_key IN (%s, %s, %s)", KEYS)
    got = {r['setting_key']: r['setting_value'] or '' for r in cur.fetchall()}
    return {k: got.get(k, '') for k in KEYS}


@app.route('/branches')
@login_required
@role_required('Admin')
@guarded
def branches():
    cur = mysql.connection.cursor()
    try:
        cfg = _settings(cur)
        local = BV.summary_counts(cur)
    except Exception:
        app.logger.exception('branch page failed')
        cfg, local = {k: '' for k in KEYS}, None
        flash_unexpected('Could not load the branch page.')
    finally:
        cur.close()
    remote, remote_error = None, ''
    if cfg['branch_url'] and cfg['branch_token'] and request.args.get('fetch') == '1':
        try:
            remote = BV.fetch_summary(cfg['branch_url'], cfg['branch_token'])
        except BV.BranchError as e:
            remote_error = str(e)
    return render_template('branches.html', cfg=cfg, local=local, remote=remote, remote_error=remote_error,
                           has_token=bool(cfg['branch_token']), shop=get_setting('shop_name'))


@app.route('/branches/save', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def branches_save():
    name = (request.form.get('branch_name') or '').strip()[:60]
    token = (request.form.get('branch_token') or '').strip()[:200]
    cur = mysql.connection.cursor()
    try:
        url = BV.validate_branch_url(request.form.get('branch_url') or '')
        current = _settings(cur)
        if not token:
            token = current['branch_token']          # empty box keeps the saved token
        if not token:
            raise BV.BranchError('Enter the API token for the other branch.')
        rows = [('branch_name', name), ('branch_url', url), ('branch_token', token)]
        for key, value in rows:
            cur.execute("""INSERT INTO app_settings (setting_key, setting_value) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)""", (key, value))
        audit(cur, 'branch.save', 'setting', 'branch', f'other branch: {name or "unnamed"}')   # the token is never logged
        mysql.connection.commit()
        flash('Other branch saved. Press "Check now" to see its numbers.', 'success')
    except BV.BranchError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        flash_unexpected('Could not save the branch settings.')
    finally:
        cur.close()
    return redirect(url_for('branches'))
