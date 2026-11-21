"""Routes: API token login/logout and server info (v88.00: the Android offline-sync snapshot was removed; see REMOVED_PHONE_CODE.md).

GET /api/sync/snapshot   Authorization: Bearer <token>  (Admin or Pharmacist)
  200 -> {"data": [medicine, ...], "meta": {"count", "snapshot_at"}}
    medicine = {medicine_id, name, category, price, stock, reorder_level, barcode,
                batches: [{batch_id, batch_number, expiry_date, quantity}, ...], sold_30d}
  Batches are live (quantity > 0, not expired) and in FIFO order (earliest expiry first).
  snapshot_at is the server clock in UTC (ISO, ends with Z). The phone uses it to refuse offline billing when its copy is too old.
  Read-only: nothing is written.

POST /api/auth/login   JSON {"username", "password", "device"}  (no token needed)
  201 -> {"token", "username", "full_name", "role"}   the token is shown once; the API client keeps it
  401 wrong password, 403 not an Admin/Pharmacist or outside the account's access hours, 429 locked
POST /api/auth/logout  Authorization: Bearer <token>   -> revokes that token
"""
from flask import g, jsonify, request  # noqa: F401
from datetime import datetime, timedelta
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.core import _lock_key, _lock_left, _register_fail, _clear_fails, DUMMY_HASH
from pharmacy.api_auth import create_token
from pharmacy.routes.api import api_required, _json_row


def _inside_access_window(cur, user_id):
    """Same rule as the web login: an account can have allowed hours (for example 09:00 to 21:00)."""
    cur.execute("SELECT access_start_time, access_end_time FROM users WHERE user_id = %s", (user_id,))
    t = cur.fetchone()
    if not t or not t['access_start_time'] or not t['access_end_time']:
        return True
    start = t['access_start_time'].total_seconds() if isinstance(t['access_start_time'], timedelta) else 0
    end = t['access_end_time'].total_seconds() if isinstance(t['access_end_time'], timedelta) else 0
    now = datetime.now()
    now_s = now.hour * 3600 + now.minute * 60 + now.second
    if start <= end:
        return start <= now_s <= end
    return now_s >= start or now_s <= end          # night shift, for example 20:00 to 06:00


@app.route('/api/auth/login', methods=['POST'])
@guarded
def api_device_login():
    body = request.get_json(silent=True) or {}
    username = str(body.get('username') or '').strip()[:60]
    password = str(body.get('password') or '')
    device = str(body.get('device') or 'Android phone').strip()[:60] or 'Android phone'
    if not username or not password:
        return jsonify(error='Enter username and password.'), 400
    lock_key = _lock_key(request.remote_addr or '?', 'phone:' + username)
    left = _lock_left(lock_key)
    if left:
        return jsonify(error='Too many wrong attempts. Wait %d minute(s) and try again.' % max(1, left // 60 + (1 if left % 60 else 0))), 429
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT u.user_id, u.full_name, u.password_hash, r.role_name
                       FROM users u JOIN roles r ON u.role_id = r.role_id
                       WHERE u.username = %s AND u.is_active = TRUE""", (username,))
        user = cur.fetchone()
        has_hash = bool(user and user['password_hash'])
        stored = user['password_hash'].encode('utf-8') if has_hash else DUMMY_HASH
        password_ok = bcrypt.checkpw(password.encode('utf-8'), stored)   # one bcrypt check either way
        if not (has_hash and password_ok):
            _register_fail(lock_key)
            audit_direct('phone.login_failed', details=device, username=username, status='denied')
            return jsonify(error='Username or password is wrong.'), 401
        if user['role_name'] not in ('Admin', 'Pharmacist'):
            audit_direct('phone.login_denied', details=device, user_id=user['user_id'], username=username, status='denied')
            return jsonify(error='Only Admin or Pharmacist accounts can use the phone app.'), 403
        if not _inside_access_window(cur, user['user_id']):
            audit_direct('phone.login_denied', details='outside access hours', user_id=user['user_id'],
                         username=username, status='denied')
            return jsonify(error='This account cannot sign in at this time (access hours).'), 403
        _clear_fails(lock_key)
        raw = create_token(cur, '%s (%s)' % (device, username), user['role_name'], user['user_id'])
        mysql.connection.commit()
        audit_direct('phone.login', details=device, user_id=user['user_id'], username=username)
        return jsonify(token=raw, username=username, full_name=user['full_name'], role=user['role_name']), 201
    finally:
        cur.close()


@app.route('/api/auth/logout', methods=['POST'])
@api_required('Admin', 'Pharmacist')
@guarded
def api_device_logout():
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE api_tokens SET revoked = 1 WHERE token_id = %s", (g.api_token['token_id'],))
        mysql.connection.commit()
    finally:
        cur.close()
    return jsonify(ok=True)


@app.route('/api/server/info')
def api_server_info():
    """v88.00: public, no secrets. API clients use it to check the server version."""
    return jsonify(app='MediGen AI Pro', version=Config.APP_VERSION)
