"""
Line-coverage report for pharmacy/ and app.py, using only the standard library
(no `coverage` package needed).

    python tests/measure_coverage.py            -> per-file table + total
    python tests/measure_coverage.py --min 80   -> exit 1 if total is below 80 %

It runs every mock test file (same set as run_all.py) in this process while
tracing which lines execute. It is an estimate of line coverage, not branch coverage.
"""
import glob, io, os, runpy, sys, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
TRACKED_DIR = os.path.join(ROOT, 'pharmacy') + os.sep
TRACKED_FILES = {os.path.join(ROOT, 'app.py')}

hits = {}

def _tracer(frame, event, arg):
    fname = frame.f_code.co_filename
    if not (fname.startswith(TRACKED_DIR) or fname in TRACKED_FILES):
        return None
    lines = hits.setdefault(fname, set())
    def local(frame, event, arg):
        if event == 'line':
            lines.add(frame.f_lineno)
        return local
    lines.add(frame.f_lineno)
    return local

def executable_lines(path):
    """Line numbers that hold code, read from the compiled module (Python 3.10+ co_lines)."""
    with open(path, encoding='utf-8') as fh:
        src = fh.read()
    code = compile(src, path, 'exec')
    found, stack = set(), [code]
    while stack:
        co = stack.pop()
        for _s, _e, line in co.co_lines():
            if line:
                found.add(line)
        stack.extend(c for c in co.co_consts if hasattr(c, 'co_lines'))
    return found

def run_tests():
    files = sorted(glob.glob(os.path.join(HERE, 'test_*.py')))
    files = [f for f in files if not f.endswith('test_live_mysql.py')]
    os.environ.setdefault('MEDIGEN_ROOT', ROOT)
    os.environ['MEDIGEN_LIVE_TEST'] = '0'
    sys.path.insert(0, ROOT)
    sys.path.insert(0, HERE)
    for f in files:
        buf = io.StringIO()
        sys.settrace(_tracer)
        try:
            with contextlib.redirect_stdout(buf):
                runpy.run_path(f, run_name='__main__')
        except SystemExit:
            pass
        except Exception:
            pass
        finally:
            sys.settrace(None)

def main():
    minimum = None
    if '--min' in sys.argv:
        minimum = float(sys.argv[sys.argv.index('--min') + 1])
    run_tests()
    targets = sorted(glob.glob(os.path.join(TRACKED_DIR, '*.py')) + glob.glob(os.path.join(TRACKED_DIR, 'routes', '*.py')))
    targets.append(os.path.join(ROOT, 'app.py'))
    total_exec = total_hit = 0
    print(f"{'module':40} {'lines':>6} {'hit':>6} {'cover':>7}")
    print('-' * 62)
    for path in targets:
        if not os.path.exists(path):
            continue
        execable = executable_lines(path)
        got = hits.get(path, set()) & execable
        total_exec += len(execable)
        total_hit += len(got)
        pct = 100.0 * len(got) / len(execable) if execable else 100.0
        print(f"{os.path.relpath(path, ROOT):40} {len(execable):>6} {len(got):>6} {pct:6.1f}%")
    total = 100.0 * total_hit / total_exec if total_exec else 0.0
    print('-' * 62)
    print(f"TOTAL line coverage: {total:.1f}%  ({total_hit}/{total_exec} lines)")
    if minimum is not None and total < minimum:
        print(f"BELOW TARGET {minimum:.0f}%")
        sys.exit(1)

if __name__ == '__main__':
    main()
