"""
MediGen AI Pro - Windows desktop launcher.

Starts the pharmacy system on this PC only (127.0.0.1) and opens it in its own
MediGen window (falls back to your web browser if that is not possible).
Closing the MediGen window stops the program. Ctrl + C in the black window also stops it.

Run it from source:      python desktop.py
Or the built program:    MediGenAIPro.exe   (see build_exe.bat)
"""
import os
import sys
import threading
import time
import webbrowser

# Frozen-app helper mode: the Settings page runs its backup and restore-test
# scripts as [sys.executable, script]. Inside the built exe there is no loose
# Python, so the exe itself runs the script file and exits:
#     MediGenAIPro.exe --script scripts\backup_db.py
if len(sys.argv) > 2 and sys.argv[1] == '--script':
    import runpy
    try:
        runpy.run_path(sys.argv[2], run_name='__main__')
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f'Script failed: {e}')
        sys.exit(1)

# Must run before config is imported: when a bundled MySQL folder exists it sets the DB_* settings.
import bundled_mysql
_db_message = bundled_mysql.start()

import config
from config import Config

PORT = Config.PORT
URL = f'http://127.0.0.1:{PORT}/'

def _banner(lines):
    width = max(len(x) for x in lines) + 4
    print('+' + '-' * width + '+')
    for x in lines:
        print('|  ' + x.ljust(width - 2) + '|')
    print('+' + '-' * width + '+')

def _admin_count():
    import MySQLdb
    db = MySQLdb.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
                         passwd=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB, charset='utf8mb4')
    try:
        cur = db.cursor()
        cur.execute('SELECT COUNT(*) FROM users')
        return cur.fetchone()[0]
    finally:
        db.close()

def _create_first_admin():
    """Same as create_admin.py, but works inside the .exe (no Python needed)."""
    import getpass
    import bcrypt
    import MySQLdb
    print()
    print('  No user account exists yet. Create the first Admin now.')
    username = input('  Admin username [admin]: ').strip() or 'admin'
    full_name = input('  Full name [Administrator]: ').strip() or 'Administrator'
    while True:
        password = getpass.getpass('  Password (min 8 characters): ')
        if len(password) < 8:
            print('  Password is too short. Try again.')
            continue
        if password != getpass.getpass('  Repeat password: '):
            print('  The two passwords do not match. Try again.')
            continue
        break
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db = MySQLdb.connect(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
                         passwd=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB, charset='utf8mb4')
    try:
        cur = db.cursor()
        cur.execute('INSERT INTO users (full_name, username, password_hash, role_id) VALUES (%s, %s, %s, 1)',
                    (full_name, username, hashed))
        db.commit()
    finally:
        db.close()
    print('  Admin account created. You can login now.')
    print()

def main():
    os.chdir(config.BASE_DIR)
    _banner(['MediGen AI Pro - starting...', f'Folder : {config.BASE_DIR}', f'Address: {URL}'])
    if _db_message:
        print('  ' + _db_message)
    if config.ENV_FILE is None and not bundled_mysql.available():
        print('  [!] .env file not found next to the program. Copy your .env there first.')

    import app as pharmacy
    try:
        from waitress import serve as _waitress_serve           # preferred: production-grade server
        def serve_forever():
            _waitress_serve(pharmacy.app, host='127.0.0.1', port=PORT, threads=8)
    except ImportError:
        print('  [i] waitress not installed: using the built-in server (fine for one PC)')
        def serve_forever():
            pharmacy.app.run(host='127.0.0.1', port=PORT, threaded=True, debug=False, use_reloader=False)

    # same start-up work as "python app.py": schema check and append-only audit
    try:
        with pharmacy.app.app_context():
            pharmacy.ensure_schema()
            pharmacy.ensure_audit_triggers()
    except Exception as e:
        print('  [!] start-up check failed:', e)
        print('      Check DB_USER / DB_PASSWORD / DB_NAME in .env and that MySQL is running.')

    # first run on an empty database: create the Admin account here
    try:
        if _admin_count() == 0:
            _create_first_admin()
    except Exception as e:
        print('  [!] Could not check or create the Admin account:', e)

    server = threading.Thread(target=serve_forever, daemon=True)
    server.start()
    time.sleep(1.2)

    # Preferred: its own MediGen window (pywebview, uses Windows WebView2).
    # Fallback: the normal web browser, if the window cannot be opened.
    try:
        import webview                                           # pip: pywebview
    except ImportError:
        webview = None
    if webview is not None:
        try:
            print('  Opening MediGen window. Close the MediGen window to stop the program.')
            webview.create_window('MediGen AI Pro', URL, width=1280, height=820, min_size=(900, 600))
            # v100.00: the WebView2 data folder is pinned to one fixed place
            # (%LOCALAPPDATA%\MediGenAIPro\WebView2). Without this, the window
            # could start with a fresh profile and 'Remember me' would look
            # broken - the sign-in cookie lives in that folder.
            _store = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.expanduser('~'), 'MediGenAIPro', 'WebView2')
            try:
                os.makedirs(_store, exist_ok=True)
                webview.start(storage_path=_store)               # blocks until the window is closed
            except TypeError:
                webview.start()                                  # old pywebview without storage_path
            print('  MediGen window closed.')
            return
        except Exception as e:
            print('  [!] Could not open the MediGen window:', e)
            print('      Opening in the web browser instead.')
    try:
        webbrowser.open(URL)
    except Exception as e:
        print('  [!] Could not open the browser automatically:', e)
        print(f'      Open this address yourself: {URL}')
    print(f'  Running. Close this window to stop MediGen. Open again any time: {URL}')
    try:
        while server.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    print('  MediGen stopped.')

if __name__ == '__main__':
    main()
