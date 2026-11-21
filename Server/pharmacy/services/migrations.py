"""Numbered schema migrations (backend track, B2).

Each change to the database is one file: database/migrations/NNN_short_name.sql (NNN = 3 digits).
Files run in number order. Each one runs once: the number is recorded in the schema_version table.
A migration that fails stops the run, nothing after it is applied, and the error is logged.

Rules for writing a migration:
- Use CREATE TABLE IF NOT EXISTS for new tables (safe to repeat).
- MySQL 8 has no ADD COLUMN IF NOT EXISTS, so column changes are NOT written as migrations yet.
  The older startup checks in core.ensure_schema() still add columns (they check information_schema first).
  Move those into numbered files step by step, once each one is tested on the shop copy.
- Separate statements with a semicolon at the end of a line. Lines starting with -- are comments.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_DIR = os.path.join(ROOT, 'database', 'migrations')
NAME_RE = re.compile(r'^(\d{3})_([a-z0-9_]+)\.sql$')

SCHEMA_VERSION_DDL = """CREATE TABLE IF NOT EXISTS schema_version (
                           version INT NOT NULL PRIMARY KEY,
                           name VARCHAR(100) NOT NULL,
                           applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""


def split_statements(text):
    body = '\n'.join(line for line in text.splitlines() if not line.strip().startswith('--'))
    return [s.strip() for s in body.split(';') if s.strip()]


def load_migrations(folder=MIGRATIONS_DIR):
    """Return [(version, name, [statements])] sorted by version. Raises ValueError on a repeated number."""
    found, seen = [], {}
    for fn in sorted(os.listdir(folder)):
        m = NAME_RE.match(fn)
        if not m:
            continue
        version, name = int(m.group(1)), m.group(2)
        if version in seen:
            raise ValueError(f'migration number {version:03d} is used twice: {seen[version]} and {fn}')
        seen[version] = fn
        with open(os.path.join(folder, fn), encoding='utf-8') as fh:
            found.append((version, name, split_statements(fh.read())))
    return sorted(found)


def pending(migrations, applied):
    return [m for m in migrations if m[0] not in applied]


def run_migrations(cur, folder=MIGRATIONS_DIR):
    """Apply every pending migration with the caller's cursor. Returns the versions applied now."""
    cur.execute(SCHEMA_VERSION_DDL)
    cur.execute("SELECT version FROM schema_version")
    applied = {int(r['version']) for r in (cur.fetchall() or [])}
    done = []
    for version, name, statements in pending(load_migrations(folder), applied):
        for statement in statements:
            cur.execute(statement)
        cur.execute("INSERT INTO schema_version (version, name) VALUES (%s,%s)", (version, name))
        done.append(version)
    return done
