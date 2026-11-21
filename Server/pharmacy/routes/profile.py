"""Routes: profile."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403



# ---------- PROFILE ----------
@app.route('/profile')
@login_required
@guarded
def profile():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT u.*, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.user_id = %s
    """, (session['user_id'],))
    user_data = cur.fetchone()
    activity = []
    try:
        cur.execute("""SELECT created_at, action, details, status, entity, entity_id, request_id
                       FROM audit_log WHERE user_id = %s ORDER BY audit_id DESC LIMIT 12""", (session['user_id'],))
        activity = cur.fetchall()
        cur.execute("""SELECT MAX(created_at) AS last_login FROM audit_log
                       WHERE user_id = %s AND action = 'login.success'""", (session['user_id'],))
        last = cur.fetchone()
        last_login = last['last_login'] if last else None
    except Exception:
        app.logger.exception('profile activity could not be loaded')
        last_login = None
    cur.close()
    if not user_data:
        flash('Your account was not found. Please login again.', 'danger')
        session.clear()
        return redirect(url_for('login'))
    return render_template('profile.html', user=user_data, activity=activity, last_login=last_login,
                           app_version=APP_VERSION)

@app.route('/profile/update', methods=['POST'])
@login_required
@guarded
def update_profile():
    """Only the fields that were sent are changed. Missing fields keep their old value (no 'None' text, no lost data)."""
    tab = request.form.get('tab', '')
    back = url_for('profile') + ('#' + tab if tab in ('personal', 'about', 'professional') else '')
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
        before = cur.fetchone()
        if not before:
            raise ValueError('Your account was not found. Please login again.')
        values = {}
        for f in PROFILE_FIELDS:
            if f in request.form:
                v = request.form.get(f, '').strip()
                values[f] = v[:2000] if f in PROFILE_LONG else v[:255]
        if 'full_name' in values and not values['full_name']:
            raise ValueError('Full name is required')
        if values.get('gender', '') not in ('', 'Male', 'Female', 'Other'):
            raise ValueError('Please choose a valid gender')
        if values.get('email') and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', values['email']):
            raise ValueError('Email address does not look right')
        if 'birthday' in values:
            if values['birthday']:
                try:
                    datetime.strptime(values['birthday'], '%Y-%m-%d')
                except ValueError:
                    raise ValueError('Birthday must be a valid date')
            values['birthday'] = values['birthday'] or None
        changed = {f: v for f, v in values.items() if (before.get(f) or None) != (v or None)}
        if not changed:
            flash('Nothing changed.', 'info')
            return redirect(back)
        sets = ", ".join(f"{f} = %s" for f in changed)
        cur.execute(f"UPDATE users SET {sets} WHERE user_id = %s", list(changed.values()) + [session['user_id']])
        audit(cur, 'profile.update', 'user', session['user_id'],
              'changed: ' + ', '.join(changed.keys()),
              before={f: before.get(f) for f in changed}, after=changed)
        mysql.connection.commit()
        flash('Profile updated successfully!', 'success')
    except ValueError as e:
        mysql.connection.rollback()
        flash(str(e), 'danger')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('profile update failed')
        flash('Could not save your profile. Please try again.', 'danger')
    finally:
        cur.close()
    return redirect(back)

def _is_image(head):
    """True when the first bytes are a real PNG, JPEG, GIF or WEBP header (not just a renamed file)."""
    return (head.startswith(b'\x89PNG\r\n\x1a\n') or head.startswith(b'\xff\xd8\xff')
            or head.startswith(b'GIF87a') or head.startswith(b'GIF89a')
            or (head[:4] == b'RIFF' and head[8:12] == b'WEBP'))


@app.route('/profile/upload_pic', methods=['POST'])
@login_required
@guarded
def upload_profile_pic():
    try:
        from werkzeug.utils import secure_filename
        file = request.files.get('profile_pic')
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
            if ext not in ('png', 'jpg', 'jpeg', 'jfif', 'gif', 'webp'):
                flash('Only PNG, JPG, JFIF, GIF or WEBP images are allowed', 'danger')
                return redirect(url_for('profile'))
            file.stream.seek(0, 2)
            size = file.stream.tell()
            file.stream.seek(0)
            if size > 2 * 1024 * 1024:
                flash('Photo must be 2 MB or smaller', 'danger')
                return redirect(url_for('profile'))
            if not _is_image(file.stream.read(16)):
                file.stream.seek(0)
                flash('The file is not a valid image', 'danger')
                return redirect(url_for('profile'))
            file.stream.seek(0)
            filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
            upload_dir = os.path.join(Config.BASE_DIR, 'static', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))

            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET profile_pic = %s WHERE user_id = %s",
                       (filename, session['user_id']))
            audit(cur, 'profile.photo', 'user', session['user_id'], filename)
            mysql.connection.commit()
            cur.close()
            flash('Profile picture updated!', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
@guarded
def change_password():
    back = 'settings_page' if request.form.get('next') == 'settings' else 'profile'
    cur = mysql.connection.cursor()
    try:
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        msg = password_error(new_password, session.get('user_name', ''))
        if msg:
            flash(msg, 'danger')
            return redirect(url_for(back))
        if new_password != confirm_password:
            flash('New password and confirm password do not match', 'danger')
            return redirect(url_for(back))

        cur.execute("SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        user_data = cur.fetchone()
        if not user_data or not bcrypt.checkpw(old_password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
            audit(cur, 'security.password_denied', 'user', session['user_id'], 'wrong current password')
            mysql.connection.commit()
            flash('Old password is incorrect', 'danger')
            return redirect(url_for(back))
        if old_password == new_password:
            flash('New password must be different from old password', 'danger')
            return redirect(url_for(back))

        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, session['user_id']))
        cur.execute("DELETE FROM remember_tokens WHERE user_id = %s", (session['user_id'],))
        audit(cur, 'security.password_changed', 'user', session['user_id'], 'own password changed')
        mysql.connection.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for(back))
    except Exception as e:
        mysql.connection.rollback()
        app.logger.exception('change password failed')
        flash_unexpected('Something went wrong.')
        return redirect(url_for(back))
    finally:
        cur.close()
