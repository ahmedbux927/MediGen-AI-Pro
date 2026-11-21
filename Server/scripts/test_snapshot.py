"""Checks the phone sync snapshot (GET /api/sync/snapshot) from any PC on the shop WiFi.

Usage (from the project folder, or any folder with Python 3):
    python scripts/test_snapshot.py http://192.168.100.9:5000 mgk_your_token

Needs only Python 3 (no extra packages). Changes nothing on the server.
Exit code 0 = all checks passed, 1 = a check failed.
"""
import datetime
import json
import sys
import urllib.error
import urllib.request


def fail(msg):
    print('FAIL:', msg)
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    base, token = sys.argv[1].rstrip('/'), sys.argv[2].strip()
    req = urllib.request.Request(base + '/api/sync/snapshot', headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            status, raw = res.status, res.read()
    except urllib.error.HTTPError as e:
        fail('server answered %s. %s' % (e.code, 'Token is wrong or not an Admin/Pharmacist token.' if e.code in (401, 403) else ''))
    except Exception as e:
        fail('could not reach %s (%s). Check the PC IP, the firewall (port 5000) and that the server is running.' % (base, e))

    print('OK: server answered HTTP', status)
    body = json.loads(raw.decode('utf-8'))
    meds = body.get('data')
    meta = body.get('meta', {})
    if not isinstance(meds, list):
        fail('"data" is not a list')

    snap = meta.get('snapshot_at', '')
    if not snap.endswith('Z'):
        fail('snapshot_at should be UTC and end with Z, got: %r' % snap)
    print('OK: snapshot_at (UTC):', snap)

    today = datetime.date.today().isoformat()
    total_batches = 0
    for m in meds:
        for key in ('medicine_id', 'name', 'price', 'batches'):
            if key not in m:
                fail('medicine %r is missing field %s' % (m.get('medicine_id'), key))
        last_expiry = ''
        for b in m['batches']:
            total_batches += 1
            if b['quantity'] <= 0:
                fail('batch %s of %s has quantity %s (should be skipped)' % (b['batch_number'], m['name'], b['quantity']))
            if b['expiry_date'] < today:
                fail('expired batch %s of %s was sent (expiry %s)' % (b['batch_number'], m['name'], b['expiry_date']))
            if b['expiry_date'] < last_expiry:
                fail('batches of %s are not in FIFO order' % m['name'])
            last_expiry = b['expiry_date']
    print('OK: no expired or empty batches; FIFO order correct')
    print('OK: %d medicines, %d live batches (server count: %s)' % (len(meds), total_batches, meta.get('count')))
    if meta.get('count') != len(meds):
        fail('meta.count (%s) does not match the list length (%d)' % (meta.get('count'), len(meds)))

    print('\nFirst 5 medicines:')
    for m in meds[:5]:
        stock = sum(b['quantity'] for b in m['batches'])
        print('  - %s | price %s | batches %d | stock in batches %d' % (m['name'], m['price'], len(m['batches']), stock))
    print('\nALL CHECKS PASSED')


if __name__ == '__main__':
    main()
