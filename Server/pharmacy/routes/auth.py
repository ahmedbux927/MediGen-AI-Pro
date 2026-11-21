"""Routes: auth."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.core import _lock_left, _register_fail, _clear_fails, _lock_key, DUMMY_HASH, _reset_hash


# ---------- LOGIN / LOGOUT ----------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
@guarded
def login():
    if request.method == 'GET' and session.get('user_id'):
        return redirect(url_for('dashboard'))   # already logged in: never show the login page
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        lock_key = _lock_key(request.remote_addr or '?', username)
        left = _lock_left(lock_key)
        if left:
            flash(f'Too many wrong attempts. Please wait {max(1, left // 60 + (1 if left % 60 else 0))} minute(s) and try again.', 'danger')
            return render_template('login.html'), 429

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT u.user_id, u.full_name, u.password_hash, r.role_name
            FROM users u JOIN roles r ON u.role_id = r.role_id
            WHERE u.username = %s AND u.is_active = TRUE
        """, (username,))
        user = cur.fetchone()
        cur.close()

        # Always run one bcrypt check, so a wrong username takes as long as a wrong password
        has_hash = bool(user and user['password_hash'])
        stored = user['password_hash'].encode('utf-8') if has_hash else DUMMY_HASH
        password_ok = bcrypt.checkpw(password.encode('utf-8'), stored)

        if has_hash and password_ok:
            if user['role_name'] != 'Admin':
                cur2 = mysql.connection.cursor()
                cur2.execute("SELECT access_start_time, access_end_time FROM users WHERE user_id=%s", (user['user_id'],))
                time_data = cur2.fetchone()
                cur2.close()

                if time_data and time_data['access_start_time'] and time_data['access_end_time']:
                    start_td = time_data['access_start_time']
                    end_td = time_data['access_end_time']
                    start_seconds = start_td.total_seconds() if isinstance(start_td, timedelta) else 0
                    end_seconds = end_td.total_seconds() if isinstance(end_td, timedelta) else 0
                    now = datetime.now()
                    current_seconds = now.hour * 3600 + now.minute * 60 + now.second
                    if start_seconds <= end_seconds:
                        allowed = start_seconds <= current_seconds <= end_seconds
                    else:  # night shift, for example 20:00 to 06:00
                        allowed = current_seconds >= start_seconds or current_seconds <= end_seconds
                    if not allowed:
                        start_str = str(start_td)[:5]
                        end_str = str(end_td)[:5]
                        flash(f'Your access time is {start_str} to {end_str}. Access denied at this time.', 'danger')
                        return render_template('login.html')

            _clear_fails(lock_key)
            audit_direct('login.success', '', user['user_id'], username)
            session.clear()                      # new session = safer
            session.permanent = True             # auto logout after idle time
            session['user_id'] = user['user_id']
            session['user_name'] = user['full_name']
            session['role'] = user['role_name']
            flash(f"Welcome {user['full_name']}!", 'success')
            if password_error(password, username):
                flash('Your password is weak. Please change it from My Profile.', 'warning')
            resp = redirect(url_for('dashboard'))
            if request.form.get('remember'):
                try:
                    resp = set_remember_cookie(resp, remember_login(user['user_id']))
                    app.logger.info('remember-me: cookie set for user %s', user['user_id'])
                    # v90.00: the user must SEE that remember-me worked
                    flash('Remember me is ON - this PC will stay signed in for 30 days. '
                          'Logging out turns it off.', 'success')
                except Exception:
                    app.logger.exception('could not save remember-me (login still works)')
                    flash('Remember me could not be saved this time - you are signed in for now.', 'warning')
            return resp

        audit_direct('login.fail', f'wrong password for {username}', None, username, status='denied')
        remaining = _register_fail(lock_key)
        if remaining > 0:
            flash(f'Invalid username or password. {remaining} attempt(s) left.', 'danger')
        else:
            audit_direct('login.locked', f'locked for {Config.LOGIN_LOCK_MINUTES} min after wrong passwords', None, username, status='denied')
            flash(f'Too many wrong attempts. Login is locked for {Config.LOGIN_LOCK_MINUTES} minutes.', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
@guarded
def logout():
    try:
        forget_login(request.cookies.get(REMEMBER_COOKIE))
    except Exception:
        app.logger.exception('could not remove remember-me token')
    session.clear()
    flash('Logged out successfully', 'info')
    return clear_remember_cookie(redirect(url_for('login')))


# ---------- FORGOT PASSWORD: user sets a new password with the Admin's one-time code ----------
@app.route('/forgot-password', methods=['GET', 'POST'])
@guarded
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')
    username = request.form.get('username', '').strip()
    code = request.form.get('reset_code', '')
    new_password = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    try:
        if not username or not code.strip():
            flash('Enter your username and the reset code from the Admin.', 'danger')
            return redirect(url_for('forgot_password'))
        lock_key = _lock_key(request.remote_addr or '?', 'reset:' + username)
        left = _lock_left(lock_key)
        if left:
            flash(f'Too many wrong codes. Wait {max(1, left // 60)} minute(s) and try again.', 'danger')
            return redirect(url_for('forgot_password'))
        if new_password != confirm:
            flash('The two passwords do not match.', 'danger')
            return redirect(url_for('forgot_password'))
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, username FROM users WHERE username=%s AND is_active=1", (username,))
        user = cur.fetchone()
        valid = False
        if user:
            cur.execute("""SELECT reset_id, code_hash FROM password_resets
                           WHERE user_id=%s AND used=0 AND expires_at > NOW()
                           ORDER BY reset_id DESC LIMIT 1""", (user['user_id'],))
            row = cur.fetchone()
            valid = bool(row) and hmac.compare_digest(row['code_hash'], _reset_hash(code))
        if not valid:
            cur.close()
            _register_fail(lock_key)
            audit_direct('password.reset_failed', details=username, username=username, status='denied')
            flash('Username, code or time is wrong. Ask the Admin for a new code.', 'danger')
            return redirect(url_for('forgot_password'))
        msg = password_error(new_password, user['username'])
        if msg:
            cur.close()
            flash(msg, 'danger')
            return redirect(url_for('forgot_password'))
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("UPDATE users SET password_hash=%s WHERE user_id=%s", (hashed, user['user_id']))
        cur.execute("UPDATE password_resets SET used=1 WHERE user_id=%s", (user['user_id'],))
        cur.execute("DELETE FROM remember_tokens WHERE user_id=%s", (user['user_id'],))
        mysql.connection.commit()
        cur.close()
        _clear_fails(lock_key)
        audit_direct('password.reset', details=username, user_id=user['user_id'], username=username)
        flash('Password changed. Please log in with the new password.', 'success')
        return redirect(url_for('login'))
    except Exception:
        flash_unexpected('Password could not be changed.')
        return redirect(url_for('forgot_password'))
