"""Routes: settings."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403


SETTING_RESET_GROUPS = {
    'shop': ('shop_name', 'shop_address', 'shop_phone', 'owner_whatsapp', 'receipt_footer'),
    'money': ('tax_rate', 'cashier_max_discount'),
}


@app.route('/settings/reset', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def settings_reset():
    """Stage 9: reset one settings group to the built-in defaults (with a
    confirmation in the page). The change is audited like any other save."""
    group = request.form.get('group') or ''
    keys = SETTING_RESET_GROUPS.get(group)
    if not keys:
        flash('Unknown settings group.', 'danger')
        return redirect(url_for('settings_page'))
    cur = mysql.connection.cursor()
    try:
        for key in keys:
            cur.execute("""INSERT INTO app_settings (setting_key, setting_value) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)""",
                        (key, SETTING_DEFAULTS.get(key, '')))
        audit(cur, 'settings.reset', 'settings', None, f'group {group} reset to defaults')
        mysql.connection.commit()
        flash('Settings reset to defaults.', 'success')
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('settings reset failed')
        flash_unexpected('Could not reset settings.')
    finally:
        cur.close()
    return redirect(url_for('settings_page', tab=group))


# ---------- SETTINGS PAGE (Admin) ----------
@app.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
@guarded
def settings_page():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        try:
            name = request.form.get('shop_name', '').strip()[:100]
            if not name:
                raise ValueError('Shop name is required')
            try:
                tax = float(request.form.get('tax_rate', '0') or 0)
                cash = float(request.form.get('cashier_max_discount', '10') or 10)
            except ValueError:
                raise ValueError('Tax and discount must be numbers')
            if not 0 <= tax <= 30:
                raise ValueError('Tax rate must be between 0 and 30 percent')
            if not 0 <= cash <= 100:
                raise ValueError('Cashier discount limit must be between 0 and 100 percent')
            values = {
                'shop_name': name,
                'shop_address': request.form.get('shop_address', '').strip()[:255],
                'shop_phone': request.form.get('shop_phone', '').strip()[:50],
                'owner_whatsapp': request.form.get('owner_whatsapp', '').strip()[:20],
                'receipt_footer': request.form.get('receipt_footer', '').strip()[:255],
                'tax_rate': f"{tax:g}",
                'cashier_max_discount': f"{cash:g}",
            }
            # v91.00: AI provider keys. A blank field keeps the saved key; the
            # clear box removes it. Key VALUES are never audited, flashed or rendered -
            # only the fact that they changed.
            ai_values = {}
            ai_changed = []
            for field in ('gemini_api_key',):
                new_key = (request.form.get(field) or '').strip()[:255]
                if request.form.get('clear_' + field):
                    ai_values[field] = ''
                    ai_changed.append(field.replace('_api_key', '') + ' key removed')
                elif new_key:
                    ai_values[field] = new_key
                    ai_changed.append(field.replace('_api_key', '') + ' key saved')
            if request.form.get('ai_pane'):   # Stage 6: daily AI summary toggle lives on the AI pane only
                values['ai_daily_summary'] = '1' if request.form.get('ai_daily_summary') else '0'
            # the audit snapshot must never contain key values
            old_settings = {k: v for k, v in get_all_settings().items() if 'api_key' not in k}
            for key, val in list(values.items()) + list(ai_values.items()):
                cur.execute("""INSERT INTO app_settings (setting_key, setting_value) VALUES (%s, %s)
                               ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)""", (key, val))
            details = f"shop={name}, tax={tax:g}%, cashier max={cash:g}%"
            if ai_changed:
                details += '; AI: ' + ', '.join(ai_changed)
            audit(cur, 'settings.update', 'settings', None, details,
                  before=old_settings, after=values)
            mysql.connection.commit()
            flash('Settings saved. New receipts will use them.', 'success')
        except ValueError as e:
            mysql.connection.rollback()
            flash(str(e), 'danger')
        except Exception as e:
            mysql.connection.rollback()
            app.logger.exception('settings save failed')
            flash_unexpected('Could not save settings.')
        finally:
            cur.close()
        return redirect(url_for('settings_page'))
    tab = request.args.get('tab', 'shop')
    if tab not in ('shop', 'money', 'security', 'ai', 'about'):
        tab = 'shop'
    # v91.00: only a masked hint reaches the page - never the key itself
    all_s = get_all_settings()
    ai_keys = {}
    for field, label in (('gemini_api_key', 'Gemini'),):
        v = (all_s.get(field) or '').strip()
        ai_keys[field] = {'label': label, 'set': bool(v), 'mask': ('••••' + v[-4:]) if len(v) >= 4 else ''}
    return render_template('settings.html', s=all_s, tab=tab, about=get_about_info(), ai_keys=ai_keys, backup=backup_status())


# ---------- AI KEY TEST (v92.00) ----------
@app.route('/settings/ai/test', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def settings_ai_test():
    """One tiny live call with the SAVED key; the reply says exactly what the
    provider answered (connected / key refused / model missing / no network)."""
    prov = (request.form.get('provider') or '').strip()
    if prov != 'gemini':
        return jsonify({'ok': False, 'message': 'Unknown provider.'}), 400
    from pharmacy.ai_client import test_provider
    ok_, msg = test_provider(prov)
    return jsonify({'ok': ok_, 'message': msg})


# ---------- BACKUP NOW (v94.00) ----------
def _script_cmd(script):
    """Command that runs one of the bundled scripts. From source this is the
    normal [python, script]; inside the built Windows exe (PyInstaller) there
    is no loose Python, so the exe runs the script itself via its --script
    mode (see desktop.py)."""
    import sys
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--script', script]
    return [sys.executable, script]


@app.route('/settings/backup-now', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def settings_backup_now():
    """Runs the same real mysqldump backup as scripts/backup_db.py and reports
    its true result. A failed dump says so; nothing is faked."""
    import os, subprocess, sys
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    script = os.path.join(root, 'scripts', 'backup_db.py')
    try:
        r = subprocess.run(_script_cmd(script), cwd=root, capture_output=True, text=True, timeout=180)
        line = next((ln for ln in (r.stdout or '').splitlines() if ln.startswith('Backup saved:')), '')
        if r.returncode == 0 and line:
            flash('Backup complete: ' + os.path.basename(line.split(':', 1)[1].strip()) + ' (Server backups folder).', 'success')
        else:
            tail = ((r.stderr or '') or (r.stdout or '')).strip().splitlines()
            flash('Backup FAILED. ' + (tail[-1][:200] if tail else 'mysqldump did not run.'), 'danger')
    except Exception as e:
        flash('Backup FAILED: ' + str(e)[:160], 'danger')
    return redirect(url_for('settings_page', tab='security'))

@app.route('/settings/restore-test', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def settings_restore_test():
    """v97: runs scripts/restore_test.py — the newest backup is restored into a
    throwaway database, counted, and the throwaway dropped. The real database
    is never touched. The flash reports the script's true verdict."""
    import os, subprocess, sys
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    script = os.path.join(root, 'scripts', 'restore_test.py')
    try:
        r = subprocess.run(_script_cmd(script), cwd=root, capture_output=True, text=True, timeout=360)
        line = next((ln for ln in (r.stdout or '').splitlines() if ln.startswith('RESTORE TEST')), '')
        if r.returncode == 0 and line.startswith('RESTORE TEST OK'):
            flash('Backup restore test PASS — ' + line.split(':', 1)[1].strip(), 'success')
        else:
            flash('Backup restore test FAILED — ' + (line.split(':', 1)[1].strip()[:200] if ':' in line else 'script did not run.'), 'danger')
    except Exception as e:
        flash('Backup restore test FAILED: ' + str(e)[:160], 'danger')
    return redirect(url_for('settings_page', tab='security'))

