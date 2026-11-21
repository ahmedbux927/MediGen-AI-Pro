"""v89.00: one-command health check for the shop PC (automation).

Checks, in order:
  1. .env exists and has the DB_* keys and SECRET_KEY (names only - values are never printed).
  2. Every Python file compiles (py_compile).
  3. Every JavaScript file parses (node --check, only when node is installed).
  4. The full mock test suite passes (tests/run_all.py).
Writes logs/self_check_report.txt and prints the same summary. Exit code 0 = all good.

Run:  python scripts/self_check.py
"""
import os
import subprocess
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
lines = []


def note(ok, text):
    lines.append(('PASS  ' if ok else 'FAIL  ') + text)
    return ok


def main():
    all_ok = True
    lines.append(f'MediGen AI Pro self-check - {datetime.now():%Y-%m-%d %H:%M}')
    lines.append(f'Folder: {ROOT}')
    lines.append('')

    env_path = os.path.join(ROOT, '.env')
    if not os.path.exists(env_path):
        all_ok = note(False, '.env file is missing (copy .env.example to .env)')
    else:
        keys = set()
        with open(env_path, encoding='utf-8-sig', errors='replace') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    keys.add(line.split('=', 1)[0].strip())
        for key in ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'SECRET_KEY'):
            all_ok = note(key in keys, f'.env has {key}') and all_ok

    import compileall
    ok_compile = compileall.compile_dir(ROOT, quiet=2, maxlevels=4)
    all_ok = note(bool(ok_compile), 'all Python files compile') and all_ok

    node = subprocess.run(['where' if os.name == 'nt' else 'which', 'node'],
                          capture_output=True, text=True).stdout.strip()
    if node:
        bad = []
        for base, _dirs, files in os.walk(os.path.join(ROOT, 'static')):
            for name in files:
                if name.endswith('.js'):
                    p = os.path.join(base, name)
                    if subprocess.run(['node', '--check', p], capture_output=True).returncode != 0:
                        bad.append(p)
        all_ok = note(not bad, f'all JavaScript files parse ({len(bad)} bad)') and all_ok
    else:
        lines.append('SKIP  node is not installed - JavaScript check skipped')

    result = subprocess.run([sys.executable, os.path.join(ROOT, 'tests', 'run_all.py')],
                            capture_output=True, text=True, cwd=ROOT)
    tail = [ln for ln in result.stdout.splitlines() if ln.startswith('TOTAL')]
    all_ok = note(result.returncode == 0, 'test suite: ' + (tail[-1] if tail else 'no result')) and all_ok

    lines.append('')
    lines.append('RESULT: ' + ('ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED - see FAIL lines above'))
    report = '\n'.join(lines)
    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    with open(os.path.join(ROOT, 'logs', 'self_check_report.txt'), 'w', encoding='utf-8') as f:
        f.write(report + '\n')
    print(report)
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
