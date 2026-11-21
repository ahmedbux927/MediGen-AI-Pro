#!/usr/bin/env bash
# Daily backup for Linux/macOS cron. Example crontab line (every day 02:30):
#   30 2 * * * /path/to/medigen/scripts/backup_db.sh >> /path/to/medigen/backups/backup.log 2>&1
cd "$(dirname "$0")/.." || exit 1
python3 scripts/backup_db.py
