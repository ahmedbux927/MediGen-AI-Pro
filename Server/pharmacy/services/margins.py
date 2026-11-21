"""Profit margin per item (v87.04). Pure rules, no database.

Margin = sale price - cost. Cost is the purchase price of the last received batch (the same cost the
reports use); if that is missing, the item's own cost price is used.
Status: no_price (sale price missing or 0), no_cost (cost missing or 0), loss (sold below cost),
low (margin under LOW_MARGIN_PCT), ok.
"""

LOW_MARGIN_PCT = 10.0
STATUS_ORDER = ('loss', 'no_price', 'no_cost', 'low', 'ok')


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def compute(price, cost):
    price, cost = _num(price), _num(cost)
    if price is None or price <= 0:
        return {'margin': None, 'pct': None, 'status': 'no_price'}
    if cost is None or cost <= 0:
        return {'margin': None, 'pct': None, 'status': 'no_cost'}
    margin = round(price - cost, 2)
    pct = round(margin / price * 100, 1)
    if pct < 0:
        status = 'loss'
    elif pct < LOW_MARGIN_PCT:
        status = 'low'
    else:
        status = 'ok'
    return {'margin': margin, 'pct': pct, 'status': status}


def pick_cost(batch_cost, item_cost):
    """Returns (cost, source). Source is 'batch', 'item' or None."""
    if _num(batch_cost) and _num(batch_cost) > 0:
        return _num(batch_cost), 'batch'
    if _num(item_cost) and _num(item_cost) > 0:
        return _num(item_cost), 'item'
    return None, None


def sort_key(row):
    """Worst first: loss, then missing price, missing cost, low margin, then healthy items. Within a status, lowest % first."""
    order = STATUS_ORDER.index(row['status'])
    pct = row['pct'] if row['pct'] is not None else 1e9
    return (order, pct, row['name'] or '')


def counts(rows):
    out = {s: 0 for s in STATUS_ORDER}
    for r in rows:
        out[r['status']] += 1
    return out
