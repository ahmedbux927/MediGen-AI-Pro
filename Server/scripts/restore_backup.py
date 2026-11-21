"""Restore a MySQL Workbench backup folder (one .sql file per table) into a NEW check database.

It never overwrites the live database. It also restores ONE .sql file made by scripts/backup_db.py
(mysqldump output, the daily backups folder). Steps:
  1. Writes into a new, empty database (default name: pharmacy_restore_check).
  2. Loads the table files first, then the views (routines file), because views need the tables.
  3. Prints the row count of every table, so you can compare with the old system.

    python scripts/restore_backup.py "C:\\backups\\Database backend backup" --prefix pharmacy_management_system
    python scripts/restore_backup.py FOLDER --prefix pharmacy_management_system --db pharmacy_restore_check
    python scripts/restore_backup.py backups\\medigen_20261025_1200.sql --db pharmacy_restore_check

Needs the mysql command-line client on PATH (it comes with MySQL 8). The password is read from .env
(MYSQL_PASSWORD) and passed through the environment, not on the command line.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)


def plan_single(path):
    """One mysqldump file: load it as a whole. It holds tables, data, views and triggers in the right order."""
    if not path.lower().endswith('.sql'):
        raise SystemExit('a single backup must be a .sql file')
    return [('whole backup', path)]


def plan_files(folder, prefix):
    """Return (table_files, view_files) for the chosen prefix, in load order."""
    tables, views = [], []
    for path in sorted(glob.glob(os.path.join(folder, f'{prefix}_*.sql'))):
        name = os.path.basename(path)[len(prefix) + 1:-4]
        (views if name == 'routines' else tables).append((name, path))
    return tables, views


def check_target(target, live_db):
    if not target or not target.replace('_', '').isalnum():
        raise SystemExit('database name may only contain letters, digits and _')
    if target == live_db:
        raise SystemExit(f'refusing: {target} is the live database. Choose a new name with --db.')


def run_mysql(args, sql=None, infile=None, env=None):
    cmd = ['mysql', '--default-character-set=utf8mb4', '-h', env['HOST'], '-u', env['USER']] + args
    stdin = open(infile, 'rb') if infile else None
    try:
        p = subprocess.run(cmd, input=sql.encode('utf-8') if sql else None, stdin=stdin,
                           capture_output=True, env=dict(os.environ, MYSQL_PWD=env['PASSWORD']))
    finally:
        if stdin:
            stdin.close()
    if p.returncode != 0:
        raise SystemExit('mysql error: ' + p.stderr.decode('utf-8', 'replace').strip())
    return p.stdout.decode('utf-8', 'replace')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('folder', help='a Workbench backup folder, or one .sql file from backups\\')
    ap.add_argument('--prefix', default='', help='for a folder: the database name in the file names, e.g. pharmacy_management_system')
    ap.add_argument('--db', default='pharmacy_restore_check')
    args = ap.parse_args()

    import config
    live = config.Config.MYSQL_DB
    check_target(args.db, live)
    if not shutil.which('mysql'):
        raise SystemExit('the mysql command-line client was not found. Add MySQL 8 bin folder to PATH.')
    single = os.path.isfile(args.folder)
    if single:
        tables, views = plan_single(args.folder), []
    else:
        if not args.prefix:
            raise SystemExit('for a folder, give --prefix (the database name in the file names)')
        tables, views = plan_files(args.folder, args.prefix)
        if not tables:
            raise SystemExit(f'no files named {args.prefix}_*.sql in {args.folder}')
    env = {'HOST': config.Config.MYSQL_HOST, 'USER': config.Config.MYSQL_USER, 'PASSWORD': config.Config.MYSQL_PASSWORD}

    existing = run_mysql(['-N', '-e', f"SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name='{args.db}'"], env=env)
    if existing.strip() == '1':
        raise SystemExit(f'{args.db} already exists. Drop it first or choose another --db name (safety stop).')
    run_mysql(['-e', f'CREATE DATABASE `{args.db}` CHARACTER SET utf8mb4'], env=env)

    loaded = 0
    for name, path in tables + views:
        run_mysql([args.db], infile=path, env=env)
        loaded += 1
        print(f'loaded {name}')
    print(f'{loaded} file(s) loaded into {args.db}. Row counts:')
    if single:
        names = [ln.strip() for ln in run_mysql(['-N', args.db, '-e', 'SHOW TABLES'], env=env).splitlines() if ln.strip()]
    else:
        names = [n for n, _ in tables]
    for n in names:
        count = run_mysql(['-N', args.db, '-e', f'SELECT COUNT(*) FROM `{n}`'], env=env).strip()
        print(f'  {n:24} {count}')
    print('Next: point MYSQL_DB in .env at the check database, start the app, and check the numbers.')


if __name__ == '__main__':
    main()
