#!/usr/bin/env python3
"""Backup restore test (v97): takes the newest backup file, restores it into a
THROWAWAY database (medigen_restore_test), counts the key tables, then drops
the throwaway database. The real database is never touched. Prints one verdict
line starting with 'RESTORE TEST OK:' or 'RESTORE TEST FAILED:'."""
import glob
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backup_db import load_settings  # noqa: E402  (reads the same .env)

TEST_DB = 'medigen_restore_test'


def _mysql(settings, args, stdin_file=None):
    env = dict(os.environ, MYSQL_PWD=settings['password'])
    kw = dict(capture_output=True, text=True, env=env, timeout=300)
    if stdin_file:
        kw['stdin'] = open(stdin_file, 'rb')
        kw['text'] = False
    return subprocess.run([settings.get('mysql', 'mysql'), '-h', settings['host'],
                           '-u', settings['user']] + args, **kw)


def main():
    settings = load_settings()
    settings['mysql'] = os.environ.get('MYSQL_BIN') or 'mysql'
    files = sorted(glob.glob(os.path.join(settings['backup_dir'], 'medigen_*.sql')), key=os.path.getmtime)
    if not files:
        print('RESTORE TEST FAILED: backups folder me koi backup file nahi mili')
        return 1
    newest = files[-1]
    try:
        r = _mysql(settings, ['-e', f'DROP DATABASE IF EXISTS {TEST_DB}; CREATE DATABASE {TEST_DB}'])
        if r.returncode != 0:
            print('RESTORE TEST FAILED: test database nahi ban saka — ' + (r.stderr or '')[:200])
            return 1
        r = _mysql(settings, [TEST_DB], stdin_file=newest)
        if r.returncode != 0:
            print('RESTORE TEST FAILED: backup import nahi ho saka — ' + ((r.stderr or b'')[:200].decode('utf-8', 'replace') if isinstance(r.stderr, bytes) else (r.stderr or '')[:200]))
            return 1
        r = _mysql(settings, ['-N', '-e',
                              'SELECT (SELECT COUNT(*) FROM medicines), (SELECT COUNT(*) FROM customers), (SELECT COUNT(*) FROM sales)', TEST_DB])
        if r.returncode != 0:
            print('RESTORE TEST FAILED: restored data parha nahi ja saka')
            return 1
        counts = (r.stdout or '0	0	0').strip().split('	')
        print(f"RESTORE TEST OK: {os.path.basename(newest)} — medicines={counts[0]} customers={counts[1]} sales={counts[2]}")
        return 0
    finally:
        try:
            _mysql(settings, ['-e', f'DROP DATABASE IF EXISTS {TEST_DB}'])
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main())
