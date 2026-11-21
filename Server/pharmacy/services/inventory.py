"""Inventory automation rules (backend track, B7). Pure functions: no database, no Flask.

- expiry_buckets: stock that expires in 0-30, 31-60 or 61-90 days, plus already expired stock.
- low_stock: severity of each medicine at or below its reorder level.
- purchase_suggestions: how much to order, grouped by the supplier it was last bought from.
The database queries and the report files are in scripts/inventory_report.py.
"""
from collections import defaultdict
from datetime import date

BUCKETS = [('expired', None, -1), ('0-30 days', 0, 30), ('31-60 days', 31, 60), ('61-90 days', 61, 90)]
TARGET_MULTIPLIER = 2          # order up to twice the reorder level


def expiry_buckets(batch_rows, today):
    """batch_rows: dicts with name, batch_number, expiry_date (date), quantity, medicine_id.
    Returns {bucket_name: [rows with days_left]}. Batches expiring after 90 days are left out."""
    out = {name: [] for name, _, _ in BUCKETS}
    for r in batch_rows:
        if not r.get('quantity') or r['quantity'] <= 0:
            continue
        days = (r['expiry_date'] - today).days
        item = dict(r, days_left=days)
        if days < 0:
            out['expired'].append(item)
        elif days <= 30:
            out['0-30 days'].append(item)
        elif days <= 60:
            out['31-60 days'].append(item)
        elif days <= 90:
            out['61-90 days'].append(item)
    for rows in out.values():
        rows.sort(key=lambda x: (x['expiry_date'], x['name']))
    return out


def low_stock(medicine_rows):
    """Items at or below their reorder level, with a severity:
    out = 0 in stock, critical = below half the reorder level, low = at or below the reorder level."""
    out = []
    for r in medicine_rows:
        stock = r.get('stock_quantity') or 0
        reorder = r.get('reorder_level') or 0
        if stock > reorder:
            continue
        if stock == 0:
            severity = 'out'
        elif stock * 2 < reorder:
            severity = 'critical'
        else:
            severity = 'low'
        out.append(dict(r, severity=severity))
    order = {'out': 0, 'critical': 1, 'low': 2}
    out.sort(key=lambda x: (order[x['severity']], x['stock_quantity'], x['name']))
    return out


def purchase_suggestions(low_rows, last_supplier):
    """last_supplier: {medicine_id: (supplier_id, supplier_name)} from the latest received purchase.
    Returns {supplier_key: {'supplier': name, 'items': [...], 'estimated_cost': Decimal-like float}}.
    Items with no purchase history go under 'No supplier history' so the owner decides."""
    groups = defaultdict(lambda: {'supplier': '', 'items': [], 'estimated_cost': 0.0})
    for r in low_rows:
        target = max(1, TARGET_MULTIPLIER * (r.get('reorder_level') or 0))
        qty = max(0, target - (r.get('stock_quantity') or 0))
        if qty == 0:
            continue
        sup = last_supplier.get(r['medicine_id'])
        key = sup[0] if sup else 'none'
        name = sup[1] if sup else 'No supplier history'
        cost = float(r.get('cost_price') or 0)
        groups[key]['supplier'] = name
        groups[key]['items'].append({'medicine_id': r['medicine_id'], 'name': r['name'], 'stock': r.get('stock_quantity') or 0,
                                     'reorder_level': r.get('reorder_level') or 0, 'order_qty': qty,
                                     'unit_cost': cost, 'line_cost': round(cost * qty, 2)})
        groups[key]['estimated_cost'] = round(groups[key]['estimated_cost'] + cost * qty, 2)
    return dict(groups)


def days_until(d, today=None):
    return (d - (today or date.today())).days
