"""POS checkout for the barcode scanner and the mobile app (backend track, v54).

Same business rules as the counter (services/sales.py): stock is reserved in id order, FIFO batches,
allergy and prescription rules, discount limits, udhaar needs a customer, double-submit guard.
Only the input differs: items may come as barcodes. No Flask here; the route reads JSON and commits.
"""
from pharmacy.services.sales import (BillError, read_lines, reserve_lines, calculate_bill, claim_guard,
                                     save_sale, check_scheduled)
from pharmacy.repos import cash_drawer as CDR   # v87.03
from pharmacy.services.cash_drawer import lock_message as cash_lock_message   # v87.03
from pharmacy.services.sale_guard import sale_fingerprint

MAX_ITEMS = 100
PAYMENTS = ('Cash', 'Card', 'Online')


class DuplicateBill(BillError):
    """The same bill was sent again within the guard window. Nothing was saved."""


def _number(value, label):
    if value is None or value == '':
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise BillError(f'{label} must be a number.')
    if number != number or number in (float('inf'), float('-inf')):
        raise BillError(f'{label} must be a number.')
    return number


def resolve_items(cur, items):
    """items = [{'barcode': '8901...', 'quantity': 2}] or [{'medicine_id': 5, 'quantity': 1}].
    Returns {medicine_id: quantity}, with the same checks as the counter."""
    if not isinstance(items, list) or not items:
        raise BillError('Add at least one item.')
    if len(items) > MAX_ITEMS:
        raise BillError(f'A bill can have at most {MAX_ITEMS} lines.')
    ids, qtys = [], []
    for item in items:
        if not isinstance(item, dict):
            raise BillError('Each item must be an object.')
        try:
            qty = int(item.get('quantity', 1))
        except (TypeError, ValueError):
            raise BillError('Quantity must be a whole number.')
        if qty <= 0:
            raise BillError('Quantity must be more than zero.')
        code = str(item.get('barcode') or '').strip()
        if code:
            cur.execute("SELECT medicine_id FROM medicines WHERE barcode = %s AND is_deleted = 0", (code,))
            row = cur.fetchone()
            if not row:
                raise BillError(f'Barcode {code} is not in the medicine list.')
            mid = row['medicine_id']
        elif item.get('medicine_id') not in (None, ''):
            try:
                mid = int(item['medicine_id'])
            except (TypeError, ValueError):
                raise BillError('medicine_id must be a number.')
        else:
            raise BillError('Each item needs a barcode or a medicine_id.')
        ids.append(str(mid))
        qtys.append(str(qty))
    return read_lines(ids, qtys)


def checkout(cur, user_id, role, body, tax_rate, cashier_max, audit_fn, offline_sync=False):
    """Save one bill. Returns {'sale_id', 'total', 'paid', 'balance'}. The caller commits.
    Raises BillError (shown to the user) or DuplicateBill (same bill sent again)."""
    if not isinstance(body, dict):
        raise BillError('Send a JSON object.')
    client_uuid = str(body.get('client_uuid') or '').strip()[:64] or None   # v86.62: offline bill id
    if client_uuid:
        cur.execute("SELECT sale_id, total_amount, paid_amount FROM sales WHERE client_uuid = %s", (client_uuid,))
        old = cur.fetchone()
        if old:   # this bill was already saved (the phone sent it again after a lost reply): return the same bill
            total = float(old['total_amount'] or 0)
            paid = float(old['paid_amount'] or 0)
            cur.execute("""SELECT subtotal_amount, discount_amount, tax_amount FROM sales WHERE sale_id = %s""", (old['sale_id'],))
            amounts = cur.fetchone() or {}
            cur.execute("SELECT medicine_name FROM sync_conflicts WHERE sale_id = %s", (old['sale_id'],))
            return {'sale_id': old['sale_id'], 'total': total, 'paid': paid,
                    'balance': round(total - paid, 2), 'already_saved': True,
                    'subtotal': float(amounts.get('subtotal_amount') or 0), 'discount': float(amounts.get('discount_amount') or 0),
                    'tax': float(amounts.get('tax_amount') or 0), 'stock_short': [r['medicine_name'] for r in cur.fetchall()]}
    wanted = resolve_items(cur, body.get('items'))
    # v87.22: remember which medicines a phone (offline) bill sells beyond the stock, for the Admin conflict list
    short_before = []
    if offline_sync:
        for mid, q in sorted(wanted.items()):
            cur.execute("SELECT name, stock_quantity FROM medicines WHERE medicine_id=%s", (mid,))
            m = cur.fetchone()
            if m and q > (m['stock_quantity'] or 0):
                short_before.append((mid, m['name'], q, m['stock_quantity'] or 0))
    # v87.21: phone sync bills (X-Offline-Sync header) are saved even when stock is short; the shortage shows in Data Quality
    lines, subtotal, _names = reserve_lines(cur, wanted, allow_short=offline_sync)

    customer_id = body.get('customer_id') or None
    rx_id = body.get('prescription_id') or None
    payment = body.get('payment_method') or 'Cash'
    if payment not in PAYMENTS:
        raise BillError('Payment must be Cash, Card or Online.')
    discount_type = 'percent' if body.get('discount_type') == 'percent' else 'amount'
    discount = _number(body.get('discount'), 'Discount')
    paid_raw = body.get('paid')
    paid = None if paid_raw in (None, '') else _number(paid_raw, 'Paid amount')

    scheduled = check_scheduled(cur, lines, rx_id)
    bill = calculate_bill(subtotal, discount, discount_type == 'percent', paid, customer_id, role,
                          cashier_max if role == 'Cashier' else None, tax_rate)

    lock = cash_lock_message(CDR.open_session(cur) is not None, payment, bill['paid'],
                             'before taking cash for this bill')          # v87.03
    if lock:
        raise BillError(lock)

    fingerprint = sale_fingerprint(user_id, customer_id, payment, rx_id, wanted,
                                   str(body.get('discount') or ''), discount_type,
                                   '' if paid is None else str(paid_raw))
    if not claim_guard(cur, fingerprint, user_id):
        raise DuplicateBill('This bill was just saved. Check the sales list before sending it again.')

    sale_id = save_sale(cur, user_id, customer_id, payment, rx_id, subtotal, bill, lines, tax_rate,
                        audit_fn, scheduled=scheduled)
    if client_uuid:
        cur.execute("UPDATE sales SET client_uuid = %s WHERE sale_id = %s", (client_uuid, sale_id))
    for mid, name, q, have in short_before:
        cur.execute("""INSERT INTO sync_conflicts (sale_id, client_uuid, medicine_id, medicine_name, requested, stock_before)
                       VALUES (%s, %s, %s, %s, %s, %s)""", (sale_id, client_uuid, mid, str(name)[:200], q, have))
    return {'sale_id': sale_id, 'total': bill['total'], 'paid': bill['paid'],
            'balance': round(bill['total'] - bill['paid'], 2),
            'subtotal': subtotal, 'discount': bill['discount'], 'tax': bill['tax'],
            'stock_short': [n for _m, n, _q, _h in short_before]}
