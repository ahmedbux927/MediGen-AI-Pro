"""MediGen AI Pro - start the web application.

The code lives in the pharmacy/ package:
  pharmacy/core.py    setup, CSRF, login lock, schema checks, decorators
  pharmacy/lib.py     shared helpers (settings, audit, prescriptions, reports, chat)
  pharmacy/routes/    one file per area (medicines, sales, purchase, ...)
Run:  python app.py
"""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.core import _FORM_RE, _add_request_id_header, _assign_request_id, _lock_left, _register_fail, _clear_fails, _lock_key, DUMMY_HASH, _schema_once, _schema_ready  # noqa: F401
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _AUDIT_INSERT, _as_date, _audit_json, _chat_reply, _chat_table_ready, _clean_doctor, _csv_response, _customer_or_error, _ensure_chat_table, _error_page, _expiry_rows, _like, _num, _read_medicine_form, _read_prescription_form, _read_purchase_rows, _report_dates, _request_context, _return_items, _sales_figures, _save_items, _stock_mismatches, _stock_rows, _valid_date  # noqa: F401
import pharmacy.routes  # noqa: F401  (registers every URL)



# ---------- RUN ----------
if __name__ == '__main__':
    import socket

    def _lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    PORT = Config.PORT

    # ---- startup check: tell the user clearly if settings or database are wrong ----
    def _check_startup():
        import config as _cfg
        if _cfg.ENV_FILE is None:
            print('  [!] .env file NOT found next to app.py -> database password is empty.')
            print('      Put the .env file in the same folder as app.py (name must be exactly ".env").')
        else:
            print('  [ok] settings loaded from', _cfg.ENV_FILE)
        try:
            import MySQLdb
            db = MySQLdb.connect(host=Config.MYSQL_HOST, user=Config.MYSQL_USER,
                                 passwd=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB)
            db.close()
            print('  [ok] database connected:', Config.MYSQL_DB)
        except Exception as e:
            print('  [!] DATABASE ERROR:', e)
            print('      Check DB_USER / DB_PASSWORD / DB_NAME in .env and that MySQL is running.')
    _check_startup()
    with app.app_context():
        ensure_schema()
        ensure_audit_triggers()
        try:   # B1 fix: drip table is ready before any sale runs
            from pharmacy.services import drip_record as _DR
            _cur = mysql.connection.cursor()
            _DR.ensure_drip_table(_cur)
            mysql.connection.commit()
            _cur.close()
        except Exception:
            app.logger.exception('drip table check failed at startup')
            print('  [!] drip table check failed - see logs\\medigen.log')
        print('  [ok] database auto-update checked')
    if Config.SECRET_KEY_GENERATED:
        print('  [!] SECRET_KEY is not set in .env - set a long random text for safety.')
    print('')
    print('  ============================================')
    print('  MediGen AI Pro v' + Config.APP_VERSION + ' is running')  # v88.00: version from Config
    print('  Code folder  :', Config.BASE_DIR)   # v87.43: shows which copy of the code is running
    print('  ============================================')
    print('  Local        : http://127.0.0.1:%s' % PORT)
    if Config.HOST in ('127.0.0.1', 'localhost'):
        print('  Shop network : OFF (APP_HOST=127.0.0.1 in .env). Set APP_HOST=0.0.0.0 and restart to allow other shop PCs.')
    else:
        print('  Shop network : http://%s:%s  (other PCs in the shop can open this in a browser)' % (_lan_ip(), PORT))
    print('  Stop server  : Ctrl + C')
    print('  ============================================')
    print('')
    # v88.00: B1 - waitress is the default production server.
    try:
        from waitress import serve as _waitress_serve
        print('  Server       : waitress (production)')
        _waitress_serve(app, host=Config.HOST, port=PORT, threads=8)
    except ImportError:
        print('  WARNING: waitress is not installed - using the Flask development server as a fallback.')
        print('  WARNING: the development server is NOT for daily shop use. Run: pip install waitress')
        app.run(host=Config.HOST, port=PORT, debug=Config.DEBUG, use_reloader=False)