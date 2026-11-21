"""Multi-branch summary (v87.11). Counts only: no medicine names, no patient names, no bill details.

- summary_counts(cur): the numbers this branch shares. Used by the API and the local page.
- validate_branch_url(url): HTTPS is required. Plain HTTP is allowed only for private LAN addresses and localhost.
- parse_summary(data): checks the remote answer has the expected numbers, so a wrong server cannot break the page.
"""
import ipaddress
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

FIELDS = ('today_revenue', 'today_invoices', 'month_revenue', 'month_invoices',
          'out_of_stock_items', 'low_stock_items', 'expiring_90_batches', 'customers_with_dues')
TIMEOUT_SECONDS = 8


class BranchError(ValueError):
    """A problem the user can fix. The message is shown as it is."""


def _is_private_host(host):
    if host in ('localhost',):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


def validate_branch_url(url):
    raw = (url or '').strip().rstrip('/')
    if not raw:
        raise BranchError('Enter the other branch address.')
    parts = urlparse(raw)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        raise BranchError('The branch address must start with https:// (or http:// for a LAN address).')
    if parts.scheme == 'http' and not _is_private_host(parts.hostname):
        raise BranchError('Use https:// for an internet address. Plain http:// is only allowed on the local network.')
    return raw


def parse_summary(data):
    if not isinstance(data, dict) or not isinstance(data.get('data'), dict):
        raise BranchError('The other branch sent an unexpected answer.')
    d = data['data']
    out = {}
    for f in FIELDS:
        v = d.get(f)
        if not isinstance(v, (int, float)) or v < 0:
            raise BranchError('The other branch sent an unexpected answer.')
        out[f] = v
    return out


def fetch_summary(base_url, token):
    base = validate_branch_url(base_url)
    if not (token or '').strip():
        raise BranchError('Enter the API token for the other branch.')
    req = urllib.request.Request(base + '/api/v1/branch/summary',
                                 headers={'Authorization': 'Bearer ' + token.strip(), 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read(200000)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise BranchError('The other branch refused the token. Check the token.')
        raise BranchError(f'The other branch answered with error {e.code}.')
    except (urllib.error.URLError, OSError, TimeoutError):
        raise BranchError('Could not reach the other branch. Check the address and that it is online.')
    try:
        return parse_summary(json.loads(body.decode('utf-8')))
    except (ValueError, UnicodeDecodeError):
        raise BranchError('The other branch sent an unexpected answer.')


def summary_counts(cur):
    cur.execute("""SELECT
                     IFNULL(SUM(CASE WHEN DATE(sale_date) = CURDATE() THEN total_amount - IFNULL(returned_amount, 0) END), 0) AS today_rev,
                     SUM(DATE(sale_date) = CURDATE()) AS today_n,
                     IFNULL(SUM(CASE WHEN sale_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01') THEN total_amount - IFNULL(returned_amount, 0) END), 0) AS month_rev,
                     SUM(sale_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')) AS month_n
                   FROM sales""")
    s = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS n FROM medicines WHERE is_deleted = 0 AND IFNULL(stock_quantity, 0) <= 0")
    out_n = cur.fetchone()['n']
    cur.execute("""SELECT COUNT(*) AS n FROM medicines WHERE is_deleted = 0 AND IFNULL(stock_quantity, 0) > 0
                   AND IFNULL(stock_quantity, 0) <= IFNULL(reorder_level, 0)""")
    low_n = cur.fetchone()['n']
    cur.execute("""SELECT COUNT(*) AS n FROM batches WHERE quantity > 0 AND expiry_date >= CURDATE()
                   AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)""")
    exp_n = cur.fetchone()['n']
    cur.execute("""SELECT COUNT(DISTINCT customer_id) AS n FROM sales WHERE customer_id IS NOT NULL
                   AND total_amount - IFNULL(returned_amount, 0) - IFNULL(paid_amount, 0) > 0.004""")
    due_n = cur.fetchone()['n']
    return {
        'today_revenue': round(float(s['today_rev'] or 0), 2), 'today_invoices': int(s['today_n'] or 0),
        'month_revenue': round(float(s['month_rev'] or 0), 2), 'month_invoices': int(s['month_n'] or 0),
        'out_of_stock_items': int(out_n or 0), 'low_stock_items': int(low_n or 0),
        'expiring_90_batches': int(exp_n or 0), 'customers_with_dues': int(due_n or 0),
    }
