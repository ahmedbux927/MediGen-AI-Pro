"""Daily MySQL backup for MediGen AI Pro (Sprint 1).

Reads the database settings from .env (the same file the app uses), runs mysqldump,
writes backups/medigen_YYYYMMDD_HHMM.sql and keeps only the newest BACKUP_KEEP files.

The password is passed to mysqldump through the MYSQL_PWD environment variable,
so it never appears in the command line or in the process list.

Run:  python scripts/backup_db.py
"""
import glob
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def read_env_file(path):
    """Simple .env reader: KEY=VALUE lines, '#' comments ignored."""
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(env=None):
    """Database settings: real environment variables win over .env, .env wins over defaults."""
    file_values = read_env_file(os.path.join(ROOT, '.env'))
    def pick(name, default):
        return (env or os.environ).get(name) or file_values.get(name) or default
    return {
        'host': pick('DB_HOST', 'localhost'),
        'user': pick('DB_USER', 'root'),
        'password': pick('DB_PASSWORD', ''),
        'name': pick('DB_NAME', 'pharmacy_management_system'),
        'mysqldump': pick('MYSQLDUMP', 'mysqldump'),
        'backup_dir': pick('BACKUP_DIR', os.path.join(ROOT, 'backups')),
        'keep': int(pick('BACKUP_KEEP', '30')),
        'offsite_dir': pick('OFFSITE_BACKUP_DIR', ''),   # v86.23: optional second copy (USB drive, network folder)
    }


def build_command(settings):
    """The mysqldump command as a list. The password is NOT in this list."""
    return [
        settings['mysqldump'],
        '--single-transaction', '--routines', '--triggers', '--events',
        '-h', settings['host'], '-u', settings['user'], settings['name'],
    ]


def backup_file_name(now=None):
    now = now or datetime.now()
    return f"medigen_{now.strftime('%Y%m%d_%H%M')}.sql"


def prune_old_backups(backup_dir, keep):
    """Delete the oldest backup files so that only the newest 'keep' files remain."""
    files = sorted(glob.glob(os.path.join(backup_dir, 'medigen_*.sql')), key=os.path.getmtime)
    removed = []
    for path in files[:max(0, len(files) - keep)]:
        os.remove(path)
        removed.append(path)
    return removed


def _remove_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def copy_offsite(path, offsite_dir):
    """Copy the new backup to the off-site folder. Returns the copied path, or raises on failure."""
    import shutil
    os.makedirs(offsite_dir, exist_ok=True)
    dest = os.path.join(offsite_dir, os.path.basename(path))
    shutil.copy2(path, dest)
    if os.path.getsize(dest) != os.path.getsize(path):
        raise RuntimeError('off-site copy size does not match')
    return dest


def run_backup(settings, now=None):
    os.makedirs(settings['backup_dir'], exist_ok=True)
    target = os.path.join(settings['backup_dir'], backup_file_name(now))
    # v88.00: write to a .tmp file first and rename only on success. A failed run must
    # never truncate or delete an earlier good backup with the same minute name.
    tmp_target = target + '.tmp'
    env = dict(os.environ, MYSQL_PWD=settings['password'])
    try:
        with open(tmp_target, 'wb') as out:
            result = subprocess.run(build_command(settings), stdout=out, stderr=subprocess.PIPE, env=env)
    except OSError as e:                # mysqldump not found or not runnable
        _remove_quietly(tmp_target)
        raise RuntimeError(f'could not start mysqldump ({e.__class__.__name__}). Set MYSQLDUMP in .env') from e
    if result.returncode != 0:
        _remove_quietly(tmp_target)     # never keep a half-written backup
        raise RuntimeError('mysqldump failed: ' + result.stderr.decode('utf-8', 'replace').strip()[:300])
    if os.path.getsize(tmp_target) < 200:   # an empty dump is a failed dump
        os.remove(tmp_target)
        raise RuntimeError('backup file is empty; check the database name and password')
    os.replace(tmp_target, target)
    removed = prune_old_backups(settings['backup_dir'], settings['keep'])
    return target, removed


if __name__ == '__main__':
    try:
        settings = load_settings()
        path, removed = run_backup(settings)
    except Exception as e:                      # the scheduler shows this in its log
        print('BACKUP FAILED:', e)
        sys.exit(1)
    print('Backup saved:', path)
    if removed:
        print('Old backups removed:', len(removed))
    if settings.get('offsite_dir'):
        try:
            print('Off-site copy saved:', copy_offsite(path, settings['offsite_dir']))
        except Exception as e:                  # the local backup is still good
            print('OFF-SITE COPY FAILED (local backup is fine):', e)
