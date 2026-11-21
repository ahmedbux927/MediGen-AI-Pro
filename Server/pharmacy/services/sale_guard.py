"""Double-submit guard for new sales (backend track, step B1).

A double click or a slow page can send the same bill twice. Each bill gets a fingerprint from the
user, customer, payment, prescription, the items with their quantities, the discount and the amount paid.
The fingerprint is stored in sale_guard with a UNIQUE key, in the same transaction as the sale.
A second identical bill inside DUPLICATE_WINDOW_SECONDS hits the key and is refused.
After the window the row is removed, so a real repeat sale later is allowed.
No template or form field changes are needed.
"""
import hashlib
import json

DUPLICATE_WINDOW_SECONDS = 10

# The table itself is created by database/migrations/002_sale_guard.sql
PURGE_SQL = f"DELETE FROM sale_guard WHERE created_at < NOW() - INTERVAL {int(DUPLICATE_WINDOW_SECONDS)} SECOND"


def sale_fingerprint(user_id, customer_id, payment, rx_id, wanted, discount, discount_type, paid):
    """wanted = {medicine_id: quantity}. The order of the items does not matter."""
    items = sorted((int(mid), int(qty)) for mid, qty in wanted.items())
    payload = [int(user_id), str(customer_id or ''), payment, str(rx_id or ''), items,
               str(discount or ''), discount_type or '', str(paid or '')]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode('utf-8')).hexdigest()


def is_duplicate_key(exc):
    """MySQL error 1062 = duplicate entry."""
    return bool(getattr(exc, 'args', None)) and exc.args[0] == 1062
