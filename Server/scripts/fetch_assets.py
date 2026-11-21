"""Download the front-end files MediGen needs, so the app works without internet.

Run ONCE on a computer that has internet access, from the project folder:
    python scripts/fetch_assets.py

It saves the files into static/vendor/. Versions are pinned, so the result is always the same.
Nothing is sent from your computer; it only downloads these public files.
"""
import os
import sys
import urllib.request

CDN = 'https://cdn.jsdelivr.net/npm/'
FILES = [
    ('bootstrap@5.3.0/dist/css/bootstrap.min.css', 'bootstrap/bootstrap.min.css'),
    ('bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js', 'bootstrap/bootstrap.bundle.min.js'),
    ('bootstrap-icons@1.10.0/font/bootstrap-icons.css', 'bootstrap-icons/bootstrap-icons.css'),
    ('bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff2', 'bootstrap-icons/fonts/bootstrap-icons.woff2'),
    ('bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff', 'bootstrap-icons/fonts/bootstrap-icons.woff'),
    ('chart.js@4.4.1/dist/chart.umd.js', 'chartjs/chart.umd.js'),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, 'static', 'vendor')


def fetch(path, target):
    url = CDN + path
    out = os.path.join(DEST, target)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as resp:
        data = resp.read()
    if len(data) < 100:
        raise RuntimeError(f'{url} returned a very small file ({len(data)} bytes)')
    with open(out, 'wb') as f:
        f.write(data)
    return len(data)


def main():
    failed = []
    for path, target in FILES:
        try:
            size = fetch(path, target)
            print(f'OK   {target} ({size // 1024} KB)')
        except Exception as e:           # keep going, report at the end
            failed.append((target, str(e)))
            print(f'FAIL {target}: {e}')
    if failed:
        print(f'\n{len(failed)} file(s) failed. Check your internet connection and run the script again.')
        return 1
    print(f'\nDone. Files saved in {DEST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
