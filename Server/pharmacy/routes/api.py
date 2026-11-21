"""REST API, read-only, for the mobile app or another branch (Sprint 3).

Every call (except /api/v1/health) needs:  Authorization: Bearer <token>
Tokens come from scripts/create_api_token.py. Responses are JSON. No passwords, no session cookies."""
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from flask import g, jsonify, request
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _like, _report_dates, _sales_figures, _stock_rows
from pharmacy.api_auth import find_token

API_VERSION = '1'


def api_required(*roles):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            header = request.headers.get('Authorization', '')
            raw = header[7:].strip() if header.lower().startswith('bearer ') else ''
            cur = mysql.connection.cursor()
            try:
                tok = find_token(cur, raw)
                mysql.connection.commit()          # saves last_used
            finally:
                cur.close()
            if not tok:
                return jsonify(error='missing or invalid token'), 401
            if roles and tok['role'] not in roles:
                return jsonify(error='this token is not allowed to read this'), 403
            g.api_token = tok
            return f(*args, **kwargs)
        return wrapper
    return deco


def _page_args(default_per=25, max_per=100):
    page = max(1, request.args.get('page', 1, type=int) or 1)
    per = min(max_per, max(1, request.args.get('per', default_per, type=int) or default_per))
    return page, per, (page - 1) * per


@app.route('/api/v1/health')
@guarded
def api_health():
    return jsonify(ok=True, api_version=API_VERSION)


@app.route('/api/v1/medicines')
@api_required('Admin', 'Pharmacist')
@guarded
def api_medicines():
    q = request.args.get('q', '').strip()[:60]
    page, per, offset = _page_args()
    is_admin = g.api_token['role'] == 'Admin'
    cols = "m.medicine_id, m.name, c.category_name AS category, m.price, m.stock_quantity AS stock, m.reorder_level, m.barcode"
    if is_admin:
        cols += ", m.cost_price"
    where, params = 'WHERE m.is_deleted = 0', []   # v86.37: hidden (deleted) medicines are not listed
    if q:
        where = "WHERE m.is_deleted = 0 AND (m.name LIKE %s OR m.barcode LIKE %s)"
        params = [_like(q), _like(q)]
    cur = mysql.connection.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) AS total FROM medicines m {where}", params)
        total = cur.fetchone()['total']
        cur.execute(f"""SELECT {cols} FROM medicines m LEFT JOIN categories c ON m.category_id = c.category_id
                        {where} ORDER BY m.name ASC LIMIT %s OFFSET %s""", params + [per, offset])
        rows = [_json_row(r) for r in cur.fetchall()]
    finally:
        cur.close()
    return jsonify(data=rows, meta={'page': page, 'per': per, 'total': total})


@app.route('/api/v1/stock/low')
@api_required('Admin', 'Pharmacist')
@guarded
def api_low_stock():
    cur = mysql.connection.cursor()
    try:
        rows = [_json_row(r) for r in _stock_rows(cur)]
    finally:
        cur.close()
    return jsonify(data=[{'name': r['name'], 'stock': r['stock_quantity'], 'reorder_level': r['reorder_level']}
                         for r in rows])


@app.route('/api/v1/batches/expiring')
@api_required('Admin', 'Pharmacist')
@guarded
def api_expiring():
    days = min(365, max(1, request.args.get('days', 90, type=int) or 90))
    cur = mysql.connection.cursor()
    try:
        cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity,
                              DATEDIFF(b.expiry_date, CURDATE()) AS days_left
                       FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                       WHERE b.quantity > 0 AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                       ORDER BY b.expiry_date ASC LIMIT 500""", (days,))
        rows = [_json_row(r) for r in cur.fetchall()]
    finally:
        cur.close()
    return jsonify(data=rows, meta={'days': days})


@app.route('/api/v1/sales/summary')
@api_required('Admin')
@guarded
def api_sales_summary():
    start, end = _report_dates()
    cur = mysql.connection.cursor()
    try:
        fig = _sales_figures(cur, start, end)
    finally:
        cur.close()
    return jsonify(data={'start': start, 'end': end,
                         'revenue': round(fig['total_revenue'], 2),
                         'invoices': fig['total_invoices'],
                         'items': fig['total_items'],
                         'profit': round(fig['total_profit'], 2)})


def _json_row(row):
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, (date, datetime)):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


@app.route('/api/v1/branch/summary')
@api_required('Admin', 'Pharmacist')
@guarded
def api_branch_summary():
    """v87.11: counts only, for the other branch. No patient or medicine details."""
    from pharmacy.services import branch_view as BV
    cur = mysql.connection.cursor()
    try:
        counts = BV.summary_counts(cur)
    finally:
        cur.close()
    return jsonify(data=counts, meta={'API_VERSION': API_VERSION})

