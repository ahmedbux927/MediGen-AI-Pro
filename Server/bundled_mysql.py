"""
MediGen AI Pro - bundled MySQL (optional, for a PC with no MySQL installed).

If the folder  mysql\\bin\\mysqld.exe  exists next to MediGen (put the unzipped
"MySQL 8.0 ZIP Archive" folder there and rename it to "mysql"), MediGen starts that
database by itself on 127.0.0.1 port 3307. Only this PC can reach it. No install and no
internet are needed.

If the folder is missing, this file does nothing and MediGen uses the database from .env.

First run: creates mysql-data\\ (the database files), sets random passwords, creates the
tables. This takes a minute. Later runs only start the server.
"""
import atexit
import json
import os
import secrets
import socket
import subprocess
import sys
import time

PORT = 3307
DB_NAME = 'pharmacy_management_system'
APP_USER = 'medigen'

BASE_DIR = (os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)))
MYSQL_DIR = os.path.join(BASE_DIR, 'mysql')
DATA_DIR = os.path.join(BASE_DIR, 'mysql-data')
CRED_FILE = os.path.join(DATA_DIR, 'credentials.json')
LOG_FILE = os.path.join(DATA_DIR, 'mysql-server.log')
SCHEMA_FILE = os.path.join(BASE_DIR, 'database', 'schema.sql')
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

_proc = None


def _tool(name):
    return os.path.join(MYSQL_DIR, 'bin', name + ('.exe' if os.name == 'nt' else ''))


def available():
    return os.path.isfile(_tool('mysqld'))


def _port_open():
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=1):
            return True
    except OSError:
        return False


def _wait_port(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if _port_open():
            return True
        time.sleep(0.5)
    return False


def _server_args():
    return [_tool('mysqld'), f'--basedir={MYSQL_DIR}', f'--datadir={DATA_DIR}', f'--port={PORT}',
            '--bind-address=127.0.0.1', '--mysqlx=OFF', '--skip-log-bin',
            '--character-set-server=utf8mb4', '--console']


def _client(user, password, sql=None, schema_file=None):
    """Run the mysql client. The password goes in an environment variable, never on the command line."""
    args = [_tool('mysql'), '--protocol=TCP', '-h', '127.0.0.1', '-P', str(PORT), '-u', user,
            '--default-character-set=utf8mb4']
    env = dict(os.environ)
    env['MYSQL_PWD'] = password
    data = None
    if sql is not None:
        data = sql.encode('utf-8')
    elif schema_file is not None:
        with open(schema_file, 'rb') as f:
            data = f.read()
    r = subprocess.run(args, input=data, capture_output=True, env=env, timeout=300, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or b'').decode('utf-8', 'replace').strip()[-300:] or 'mysql client failed')


def _initialize():
    os.makedirs(DATA_DIR, exist_ok=True)
    r = subprocess.run([_tool('mysqld'), f'--basedir={MYSQL_DIR}', f'--datadir={DATA_DIR}',
                        '--initialize-insecure', '--console'],
                       capture_output=True, timeout=600, creationflags=NO_WINDOW)
    if r.returncode != 0:
        raise RuntimeError('database files could not be created: '
                           + (r.stderr or b'').decode('utf-8', 'replace')[-300:])


def _first_setup():
    root_pw = secrets.token_urlsafe(18)          # URL-safe characters only: safe inside SQL quotes
    app_pw = secrets.token_urlsafe(18)
    _client('root', '', sql=f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{root_pw}';")
    _client('root', root_pw, sql=f"""
CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '{APP_USER}'@'localhost' IDENTIFIED BY '{app_pw}';
CREATE USER IF NOT EXISTS '{APP_USER}'@'127.0.0.1' IDENTIFIED BY '{app_pw}';
GRANT ALL PRIVILEGES ON {DB_NAME}.* TO '{APP_USER}'@'localhost';
GRANT ALL PRIVILEGES ON {DB_NAME}.* TO '{APP_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
""")
    _client('root', root_pw, schema_file=SCHEMA_FILE)   # tables, triggers, roles, first admin
    with open(CRED_FILE, 'w', encoding='utf-8') as f:
        json.dump({'root': root_pw, 'app': app_pw}, f)


def _read_creds():
    with open(CRED_FILE, encoding='utf-8') as f:
        return json.load(f)


def stop():
    global _proc
    if _proc is not None and _proc.poll() is None:
        _proc.terminate()
        try:
            _proc.wait(20)
        except subprocess.TimeoutExpired:
            _proc.kill()
    _proc = None


def start():
    """Start the bundled server if it is there.
    Returns None when there is no bundled MySQL. Otherwise returns a message for the console.
    On success it sets the DB_* environment variables, so config.py connects to this server."""
    global _proc
    if not available():
        return None
    try:
        first = not os.path.isfile(CRED_FILE)
        if first and os.path.isdir(os.path.join(DATA_DIR, 'mysql')):
            raise RuntimeError('the mysql-data folder is from an unfinished setup. '
                               'Delete the mysql-data folder and start MediGen again.')
        if first:
            _initialize()
        if not _port_open():
            logf = open(LOG_FILE, 'a', encoding='utf-8')
            _proc = subprocess.Popen(_server_args(), stdout=logf, stderr=logf, creationflags=NO_WINDOW)
            atexit.register(stop)
            if not _wait_port(60):
                raise RuntimeError(f'MySQL did not start. Read this log file: {LOG_FILE}')
        if first:
            _first_setup()
        creds = _read_creds()
    except Exception as e:
        stop()
        return f'[!] Bundled MySQL problem: {e}'
    os.environ.update({'DB_HOST': '127.0.0.1', 'DB_PORT': str(PORT), 'DB_USER': APP_USER,
                       'DB_PASSWORD': creds['app'], 'DB_NAME': DB_NAME})
    return f'Bundled database running on 127.0.0.1:{PORT} (no MySQL install needed).'
