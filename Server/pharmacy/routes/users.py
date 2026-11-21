"""Routes: users."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import user_history as UH
from pharmacy.core import _reset_hash


# ================= USERS MANAGEMENT =================
@app.route('/users')
@login_required
@role_required('Admin')
@guarded
def users():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.*, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        ORDER BY u.user_id ASC
    """)
    data = cur.fetchall()
    cur.execute("SELECT * FROM roles")
    roles = cur.fetchall()
    cur.close()
    return render_template('users.html', users=data, roles=roles)

@app.route('/users/add', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def add_user():
    try:
        d = request.form
        full_name = d['full_name'].strip()
        username = d['username'].strip()
        password = d['password']
        role_id = d['role_id']

        if not re.fullmatch(r'[A-Za-z0-9_.]{3,40}', username):
            flash('Username must be 3 to 40 letters, numbers, dot or underscore', 'danger')
            return redirect(url_for('users'))
        if not 2 <= len(full_name) <= 80:
            flash('Full name must be 2 to 80 characters', 'danger')
            return redirect(url_for('users'))
        if not str(role_id).isdigit():
            flash('Please choose a valid role', 'danger')
            return redirect(url_for('users'))

        msg = password_error(password, username)
        if msg:
            flash(msg, 'danger')
            return redirect(url_for('users'))

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            cur.close()
            flash('Username already exists', 'danger')
            return redirect(url_for('users'))
        cur.execute("SELECT role_id FROM roles WHERE role_id=%s", (int(role_id),))
        if not cur.fetchone():
            cur.close()
            flash('Please choose a valid role', 'danger')
            return redirect(url_for('users'))

        cur.execute("""INSERT INTO users (full_name, username, password_hash, role_id)
                       VALUES (%s, %s, %s, %s)""",
                    (full_name, username, hashed, role_id))
        audit(cur, 'user.add', 'user', None, f"{username} ({full_name})")
        mysql.connection.commit()
        cur.close()
        flash('User added successfully!', 'success')
    except Exception as e:
        flash_unexpected('User could not be added.', ERROR_CODES['user_add'])
    return redirect(url_for('users'))

@app.route('/users/edit/<int:uid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def edit_user(uid):
    """Stage 9: change a user's full name and role. The last active Admin
    cannot be demoted - the shop must always keep one working Admin login."""
    try:
        full_name = (request.form.get('full_name') or '').strip()
        role_id = request.form.get('role_id') or ''
        if not 2 <= len(full_name) <= 80:
            flash('Full name must be 2 to 80 characters', 'danger')
            return redirect(url_for('users'))
        if not str(role_id).isdigit():
            flash('Please choose a valid role', 'danger')
            return redirect(url_for('users'))
        cur = mysql.connection.cursor()
        cur.execute("""SELECT u.username, r.role_name FROM users u
                       JOIN roles r ON r.role_id = u.role_id WHERE u.user_id=%s""", (uid,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('User not found.', 'danger')
            return redirect(url_for('users'))
        cur.execute("SELECT role_name FROM roles WHERE role_id=%s", (int(role_id),))
        new_role = cur.fetchone()
        if not new_role:
            cur.close()
            flash('Please choose a valid role', 'danger')
            return redirect(url_for('users'))
        if row['role_name'] == 'Admin' and new_role['role_name'] != 'Admin':
            cur.execute("""SELECT COUNT(*) AS n FROM users u JOIN roles r ON r.role_id = u.role_id
                           WHERE r.role_name='Admin' AND u.is_active=1 AND u.user_id<>%s""", (uid,))
            if cur.fetchone()['n'] == 0:
                cur.close()
                flash('This is the only active Admin. Make another user Admin first.', 'danger')
                return redirect(url_for('users'))
        cur.execute("UPDATE users SET full_name=%s, role_id=%s WHERE user_id=%s",
                    (full_name, int(role_id), uid))
        audit(cur, 'user.edit', 'user', uid,
              f"{row['username']}: {row['role_name']} -> {new_role['role_name']}, name set to {full_name}")
        mysql.connection.commit()
        cur.close()
        flash('User updated successfully!', 'success')
    except Exception:
        flash_unexpected('User could not be updated.')
    return redirect(url_for('users'))


@app.route('/users/delete/<int:uid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def delete_user(uid):
    if uid == session.get('user_id'):
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('users'))
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT username FROM users WHERE user_id=%s", (uid,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('User not found.', 'danger')
            return redirect(url_for('users'))
        username = row['username']
        if username == 'deleted-user':
            cur.close()
            flash('The Deleted user account keeps old records readable. It cannot be removed.', 'danger')
            return redirect(url_for('users'))
        # The shop must never be left without an active Admin.
        cur.execute("""SELECT r.role_name FROM users u JOIN roles r ON r.role_id = u.role_id
                       WHERE u.user_id=%s""", (uid,))
        role_row = cur.fetchone()
        if role_row and role_row['role_name'] == 'Admin':
            cur.execute("""SELECT COUNT(*) AS n FROM users u JOIN roles r ON r.role_id = u.role_id
                           WHERE r.role_name='Admin' AND u.is_active=1 AND u.user_id<>%s""", (uid,))
            if int((cur.fetchone() or {}).get('n') or 0) == 0:
                cur.close()
                flash('This is the only active Admin. Make another user Admin first.', 'danger')
                return redirect(url_for('users'))
        # Every row pointing at this user: user_id columns AND foreign keys with
        # other names (counted_by, created_by, ...). Records must stay readable,
        # so by default a user with history is turned OFF, not deleted.
        counts = UH.all_references(cur, uid)
        force = request.form.get('force') == '1'
        # Login-related rows have no history value: always remove them.
        for t in UH.LOGIN_TABLES:
            cur.execute(f"DELETE FROM `{t}` WHERE user_id=%s", (uid,))
        if counts and force:
            # Permanent delete, the way the owner asked: the person's records
            # move to the 'Deleted user' placeholder, then the account goes.
            placeholder = UH.placeholder_user(cur)
            UH.reassign_references(cur, uid, placeholder)
            cur.execute("DELETE FROM users WHERE user_id=%s", (uid,))
            audit(cur, 'user.delete', 'user', uid, username)
            mysql.connection.commit()
            cur.close()
            flash(f"User {username} deleted permanently. Their records ({UH.summary(counts)}) now show "
                  "under 'Deleted user', so the shop history stays complete.", 'success')
        elif counts:
            cur.execute("UPDATE users SET is_active=0 WHERE user_id=%s", (uid,))
            audit(cur, 'user.deactivate', 'user', uid, username)
            mysql.connection.commit()
            cur.close()
            flash(f"{username} has work history ({UH.summary(counts)}), so the account was turned OFF instead "
                  "of deleted. Nothing was lost. To remove the account fully, use Delete and tick "
                  "'Delete permanently'.", 'warning')
        else:
            cur.execute("DELETE FROM users WHERE user_id=%s", (uid,))
            audit(cur, 'user.delete', 'user', uid, username)
            mysql.connection.commit()
            cur.close()
            flash(f"User {username} deleted.", 'success')
    except Exception as e:
        try:
            mysql.connection.rollback()
        except Exception as rb_exc:
            app.logger.warning('rollback after delete_user failed (%s)', type(rb_exc).__name__)
        app.logger.exception('delete_user failed for user_id=%s', uid)
        if 'foreign key' in str(e).lower() or '1451' in str(e):
            flash('This user cannot be deleted because records still point to them. '
                  'Turn the account OFF instead.', 'danger')
        else:
            flash_unexpected('User could not be deleted.')
    return redirect(url_for('users'))

@app.route('/users/toggle/<int:uid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def toggle_user(uid):
    if uid == session.get('user_id'):
        flash('You cannot deactivate your own account', 'danger')
        return redirect(url_for('users'))
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET is_active = NOT is_active WHERE user_id=%s", (uid,))
        audit(cur, 'user.toggle', 'user', uid, 'active status changed')
        mysql.connection.commit()
        cur.close()
        flash('User status updated successfully', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')
    return redirect(url_for('users'))

@app.route('/users/set_time/<int:uid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def set_user_time(uid):
    try:
        start_time = request.form['access_start_time']
        end_time = request.form['access_end_time']
        hhmm = r'([01]\d|2[0-3]):[0-5]\d'
        if not (re.fullmatch(hhmm, start_time) and re.fullmatch(hhmm, end_time)):
            flash('Access time must be in HH:MM format (24 hour)', 'danger')
            return redirect(url_for('users'))
        cur = mysql.connection.cursor()
        cur.execute("""UPDATE users
                       SET access_start_time=%s, access_end_time=%s
                       WHERE user_id=%s""",
                    (start_time, end_time, uid))
        audit(cur, 'user.access_time', 'user', uid, f"{start_time} to {end_time}")
        mysql.connection.commit()
        cur.close()
        flash('User access time updated successfully!', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')
    return redirect(url_for('users'))


@app.route('/users/reset_password/<int:uid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def reset_user_password(uid):
    """Admin sets a new password for another user (the 'forgot password' path)."""
    try:
        if uid == session.get('user_id'):
            flash('Use My Profile to change your own password.', 'warning')
            return redirect(url_for('users'))
        new_password = request.form.get('new_password', '')
        cur = mysql.connection.cursor()
        cur.execute("SELECT username FROM users WHERE user_id=%s", (uid,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('User not found.', 'danger')
            return redirect(url_for('users'))
        msg = password_error(new_password, row['username'])
        if msg:
            cur.close()
            flash(msg, 'danger')
            return redirect(url_for('users'))
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("UPDATE users SET password_hash=%s WHERE user_id=%s", (hashed, uid))
        cur.execute("DELETE FROM remember_tokens WHERE user_id=%s", (uid,))
        audit(cur, 'user.reset_password', 'user', uid, row['username'])
        mysql.connection.commit()
        cur.close()
        flash('Password reset. Tell the user their new password privately.', 'success')
    except Exception:
        flash_unexpected('Password could not be reset.')
    return redirect(url_for('users'))


_RESET_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # no 0/O/1/I to avoid confusion
RESET_MINUTES = 15


@app.route('/users/reset_code/<int:uid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def reset_user_code(uid):
    """Admin makes a one-time code (valid 15 minutes). The user types it on the Forgot password page."""
    try:
        if uid == session.get('user_id'):
            flash('Use My Profile to change your own password.', 'warning')
            return redirect(url_for('users'))
        cur = mysql.connection.cursor()
        cur.execute("SELECT username FROM users WHERE user_id=%s", (uid,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('User not found.', 'danger')
            return redirect(url_for('users'))
        raw = ''.join(secrets.choice(_RESET_ALPHABET) for _ in range(8))
        code = f"{raw[:4]}-{raw[4:]}"
        cur.execute("UPDATE password_resets SET used=1 WHERE user_id=%s AND used=0", (uid,))
        cur.execute("""INSERT INTO password_resets (user_id, code_hash, expires_at, used)
                       VALUES (%s, %s, NOW() + INTERVAL %s MINUTE, 0)""",
                    (uid, _reset_hash(raw), RESET_MINUTES))
        audit(cur, 'user.reset_code', 'user', uid, row['username'])
        mysql.connection.commit()
        cur.close()
        flash(f"Reset code for {row['username']}: {code}  (valid {RESET_MINUTES} minutes, one use). "
              "Give it to the user in person.", 'success')
    except Exception:
        flash_unexpected('Reset code could not be made.')
    return redirect(url_for('users'))
