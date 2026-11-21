"""
Run all tests and print one summary.

    python tests/run_all.py            -> mock tests (no MySQL needed, runs in seconds)
    python tests/run_all.py --live     -> also the live MySQL test (needs MySQL + TEST_DB_* settings)

Exit code 0 = everything passed.  Any FAIL or crash = exit code 1.
"""
import glob, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))

def run_one(path, live=False):
    started = time.time()
    extra = {'MEDIGEN_ROOT': ROOT, 'MEDIGEN_LIVE_TEST': '1' if live else '0'}
    p = subprocess.run([sys.executable, path], capture_output=True, text=True, cwd=ROOT, env=dict(os.environ, **extra))
    out = p.stdout + p.stderr
    passed = sum(1 for ln in out.splitlines() if ln.startswith('PASS'))
    failed = [ln for ln in out.splitlines() if ln.startswith('FAIL')]
    crashed = p.returncode != 0 or 'Traceback (most recent call last)' in p.stdout
    return passed, failed, crashed, time.time() - started, out

def main():
    live = '--live' in sys.argv
    files = sorted(glob.glob(os.path.join(HERE, 'test_*.py')))
    if not live:
        files = [f for f in files if not f.endswith(('test_live_mysql.py', 'test_live_backend.py'))]
    if live and not os.environ.get('TEST_DB_USER'):
        print('NOTE: set TEST_DB_HOST / TEST_DB_USER / TEST_DB_PASSWORD for the live test (defaults: localhost, root, empty).')
    total_pass = total_fail = 0
    bad = False
    print(f"{'suite':36} {'pass':>5} {'fail':>5}  time")
    print('-' * 60)
    for f in files:
        name = os.path.basename(f)
        passed, failed, crashed, secs, out = run_one(f, live=live and f.endswith(('test_live_mysql.py', 'test_live_backend.py')))
        total_pass += passed
        total_fail += len(failed) + (1 if crashed and not failed else 0)
        flag = '  <-- CRASH' if crashed else ('  <-- FAIL' if failed else '')
        print(f"{name:36} {passed:>5} {len(failed):>5}  {secs:4.1f}s{flag}")
        for ln in failed:
            print('      ' + ln)
        if crashed and not failed:
            print('      ' + '\n      '.join(out.strip().splitlines()[-6:]))
        bad = bad or bool(failed) or crashed
    print('-' * 60)
    print(f"TOTAL: {total_pass} passed, {total_fail} failed")
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
