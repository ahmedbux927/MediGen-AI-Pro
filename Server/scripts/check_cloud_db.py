"""Check the cloud MySQL connection (v87.19). Read only. Never prints the password.

Reads CLOUD_DB_HOST, CLOUD_DB_PORT, CLOUD_DB_NAME, CLOUD_DB_USER, CLOUD_DB_PASSWORD from the
.env file in the app folder. Uses TLS when the server offers it.

Run on the shop PC, from the app folder:
    python scripts\\check_cloud_db.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def read_env(path):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            values[key.strip()] = value.strip()
    return values


def fail(msg):
    print('FAIL: ' + msg)
    sys.exit(1)


def main():
    env = read_env(os.path.join(ROOT, '.env'))
    host = env.get('CLOUD_DB_HOST', '')
    port = env.get('CLOUD_DB_PORT', '3306') or '3306'
    name = env.get('CLOUD_DB_NAME', '')
    user = env.get('CLOUD_DB_USER', '')
    password = env.get('CLOUD_DB_PASSWORD', '')

    missing = [k for k, v in (('CLOUD_DB_HOST', host), ('CLOUD_DB_NAME', name),
                              ('CLOUD_DB_USER', user), ('CLOUD_DB_PASSWORD', password)) if not v]
    if missing:
        fail('These keys are empty in .env: ' + ', '.join(missing))
    if not port.isdigit():
        fail('CLOUD_DB_PORT must be a number.')

    try:
        import MySQLdb  # installed with the app (flask-mysqldb)
        driver = 'MySQLdb'
        conn = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=name,
                               connect_timeout=10, ssl={'ssl': True})
    except ImportError:
        fail('MySQLdb is not installed. Run: pip install -r requirements.txt')
    except Exception as exc:  # noqa: BLE001 - report the driver message, without the password
        code = exc.args[0] if getattr(exc, 'args', None) else ''
        if code == 1045:
            fail('Login refused. Check CLOUD_DB_USER and CLOUD_DB_PASSWORD.')
        if code == 1049:
            fail('Database not found. Check CLOUD_DB_NAME.')
        if code == 2003:
            fail('Cannot reach the server. Check CLOUD_DB_HOST, the port, and the shop IP in the authorized networks.')
        fail('Connection failed (%s). Check host, port, user, password and the shop IP.' % (code or 'unknown'))

    try:
        cur = conn.cursor()
        cur.execute('SELECT VERSION()')
        version = cur.fetchone()[0]
        cur.execute("SHOW STATUS LIKE 'Ssl_cipher'")
        row = cur.fetchone()
        tls = bool(row and row[1])
        cur.close()
    finally:
        conn.close()

    print('OK: connected with %s' % driver)
    print('Server version: %s' % version)
    print('Database: %s' % name)
    print('Encrypted (TLS): %s' % ('yes' if tls else 'NO. Turn on SSL in the Cloud SQL settings.'))
    sys.exit(0 if tls else 2)


if __name__ == '__main__':
    main()
