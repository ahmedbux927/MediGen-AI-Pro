"""B4: remove leftover PowerShell lines from a .env file, safely.

Usage (on the shop PC, from the Server folder):
    python scripts\\clean_env_copy.py            -> reads .env, writes .env.cleaned
Then check .env.cleaned, and if it looks right, rename it to .env yourself
(the old .env is never overwritten by this script).

Rules:
- Keep: blank lines, comment lines (#...), and lines like NAME=value (NAME in capitals).
- Remove: every other line (for example lines starting with $, [, Write-Host, if (, etc.).
- Values are NEVER printed. Only line numbers and key names are shown.
"""
import os
import re
import sys

KEEP = re.compile(r'^\s*([A-Z][A-Z0-9_]*)\s*=')
REQUIRED = ('DB_PASSWORD', 'DB_NAME', 'SECRET_KEY')


def clean_env(text):
    """Return (cleaned_text, removed_line_numbers, missing_required_keys). No values are returned for logging."""
    kept, removed, present = [], [], set()
    for no, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith('#'):
            kept.append(line)
            continue
        m = KEEP.match(line)
        if m:
            kept.append(line)
            if line.split('=', 1)[1].strip():
                present.add(m.group(1))
            continue
        removed.append(no)
    missing = [k for k in REQUIRED if k not in present]
    return '\n'.join(kept) + '\n', removed, missing


def main(path):
    if not os.path.exists(path):
        print(f'ERROR: file not found: {path}')
        return 1
    with open(path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    cleaned, removed, missing = clean_env(text)
    out = path + '.cleaned'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    print(f'Written: {out}')
    print(f'Lines removed: {len(removed)} (line numbers: {", ".join(map(str, removed)) or "none"})')
    if missing:
        print('WARNING: these required settings are missing or empty: ' + ', '.join(missing))
        print('         Add them before using the cleaned file. Values are not shown here.')
    print('Next: check the .cleaned file, then rename it to .env yourself. The old .env was not changed.')
    return 0


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    sys.exit(main(os.path.abspath(target)))
