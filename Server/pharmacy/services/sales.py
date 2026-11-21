"""New sale: business rules (backend track, B3).

The route reads the form, calls these functions, then flashes and redirects. Problems the cashier can fix
raise BillError, whose message is shown as it is. Every other exception is a bug or a database failure.
Nothing here calls Flask, so the rules can be tested without a web server.
"""
from pharmacy.errors import MediGenError
from pharmacy.services.sale_guard import PURGE_SQL, is_duplicate_key
from pharmacy.services.controlled_register import scheduled_items, prescription_missing, entries_for_sale, write_entries
from pharmacy.services import drip_record as DR

MAX_QTY = 100000
MAX_LINES = 100
TOLERANCE = 0.004        # rupees: smaller differences count as paid in full


class BillError(MediGenError, ValueError):
    """A problem with the bill that the cashier can fix. The message is shown to the user.
    Stage 2: also a typed MediGenError, so uncaught bill problems get the friendly
    typed-error page/JSON instead of a generic 500. Still a ValueError for old catch sites."""


def read_lines(medicine_ids, quantities):
    """Join repeated medicines. Returns {medicine_id: quantity}. Lines with no id or quantity are ignored."""
    wanted = {}
    for mid, q in zip(medicine_ids, quantities):
        if not mid or not q:
            continue
        if not str(mid).strip().isdigit():
            raise BillError('Invalid medicine selected. Please choose again.')
        q = int(q)                      # non-numeric text raises ValueError, shown as "Invalid number format"
        if q <= 0:
            continue
        if q > MAX_QTY:
            raise BillError('Quantity is too large')
        wanted[int(mid)] = wanted.get(int(mid), 0) + q
    if not wanted:
        raise BillError('Please add at least one medicine with a valid quantity')
    if len(wanted) > MAX_LINES:
        raise BillError(f'A bill can have at most {MAX_LINES} different medicines')
    return wanted


def pick_batches(cur, mid, q, name, allow_short=False):
    """Oldest expiry first. Expired batches are never sold. Medicines without batch records sell with batch NULL.
    allow_short (offline sync only): units that no batch can cover are sold with batch NULL, so the medicine
    stock goes below zero and Data Quality shows it."""
    cur.execute("SELECT COUNT(*) AS n FROM batches WHERE medicine_id=%s", (mid,))
    if cur.fetchone()['n'] == 0:
        return [(None, q)]
    cur.execute("""SELECT batch_id, quantity FROM batches
                   WHERE medicine_id=%s AND quantity > 0 AND expiry_date >= CURDATE()
                   ORDER BY expiry_date ASC, batch_id ASC FOR UPDATE""", (mid,))
    parts, need = [], q
    for b in cur.fetchall():
        take = min(b['quantity'], need)
        parts.append((b['batch_id'], take))
        need -= take
        if need == 0:
            break
    if need > 0 and allow_short:
        parts.append((None, need))
        return parts
    if need > 0:
        raise BillError(f"Only {q - need} unexpired units of {name} can be sold. "
                        "Expired batches cannot be sold (see Batches page).")
    return parts


def reserve_lines(cur, wanted, allow_short=False):
    """Lock the medicine rows in id order (no deadlock between two sales), check stock, pick batches.
    Returns (lines, subtotal, medicine_names); lines = [(medicine_id, unit_price, [(batch_id, qty)])]."""
    lines, subtotal, names = [], 0.0, []
    for mid in sorted(wanted):
        q = wanted[mid]
        cur.execute("SELECT name, price, stock_quantity FROM medicines WHERE medicine_id=%s FOR UPDATE", (mid,))
        med = cur.fetchone()
        if not med:
            # never bill silently without an item: the medicine was deleted after the page loaded
            raise BillError('A selected medicine no longer exists. Please reload the page and try again.')
        if q > (med['stock_quantity'] or 0) and not allow_short:
            raise BillError(f"Insufficient stock for {med['name']}! Available: {med['stock_quantity']}")
        parts = pick_batches(cur, mid, q, med['name'], allow_short=allow_short)
        price = float(med['price'] or 0)
        subtotal += price * q
        lines.append((mid, price, parts))
        names.append(med['name'])
    if not lines:
        raise BillError('Selected medicines were not found')
    return lines, round(subtotal, 2), names


def calculate_bill(subtotal, discount_value, is_percent, paid_value, customer_id, role, cashier_max, tax_rate):
    """Discount, tax, total and amount paid. paid_value None = paid in full. cashier_max only matters for Cashier."""
    if discount_value < 0:
        raise BillError('Discount cannot be negative')
    if is_percent:
        if discount_value > 100:
            raise BillError('Discount cannot be more than 100%')
        discount = round(subtotal * discount_value / 100, 2)
    else:
        discount = round(discount_value, 2)
    if discount > subtotal:
        raise BillError('Discount cannot be more than the bill amount')
    pct = (discount / subtotal * 100) if subtotal else 0
    if role == 'Cashier' and pct > cashier_max + 1e-9:
        raise BillError(f'Cashier can give at most {cashier_max:g}% discount. Please ask a Pharmacist or Admin.')
    tax = round((subtotal - discount) * tax_rate / 100, 2)
    total = round(subtotal - discount + tax, 2)
    paid = total if paid_value is None else round(paid_value, 2)
    if paid < 0 or paid > total:
        raise BillError('Paid amount must be between 0 and the total')
    if total - paid > TOLERANCE and not customer_id:
        raise BillError('A sale with a balance (credit) needs a customer. Please choose or add one.')
    return {'discount': discount, 'tax': tax, 'total': total, 'paid': paid}


def claim_guard(cur, fingerprint, user_id):
    """False when the same bill was just saved (double submit). See services/sale_guard.py."""
    cur.execute(PURGE_SQL)
    try:
        cur.execute("INSERT INTO sale_guard (fingerprint, user_id) VALUES (%s,%s)", (fingerprint, user_id))
    except Exception as e:
        if is_duplicate_key(e):
            return False
        raise
    return True


def check_scheduled(cur, lines, rx_id):
    """Scheduled medicines (set by the pharmacist) need a prescription on the bill. Returns {medicine_id: (schedule, name)}."""
    scheduled = scheduled_items(cur, [mid for mid, _p, _parts in lines])
    missing = prescription_missing(scheduled, rx_id)
    if missing:
        raise BillError('Prescription needed for: ' + ', '.join(missing) + '. Attach the prescription to this bill.')
    return scheduled


def save_sale(cur, user_id, customer_id, payment, rx_id, subtotal, bill, lines, tax_rate, audit_fn, scheduled=None, drip_routes=None):
    """Write the sale, its items, the payment and the audit row. The caller commits. Returns the sale id."""
    total, paid, discount, tax = bill['total'], bill['paid'], bill['discount'], bill['tax']
    cur.execute("""INSERT INTO sales (customer_id, user_id, payment_method, total_amount, subtotal_amount,
                                      discount_amount, tax_rate, tax_amount, paid_amount, prescription_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (customer_id, user_id, payment, total, subtotal, discount, tax_rate, tax, paid, rx_id))
    sale_id = cur.lastrowid
    for mid, price, parts in lines:
        for batch_id, take in parts:            # the trigger lowers medicine and batch stock
            cur.execute("""INSERT INTO sale_items (sale_id, medicine_id, batch_id, quantity, unit_price, subtotal)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (sale_id, mid, batch_id, take, price, round(price * take, 2)))
    DR.auto_record_sale(cur, sale_id, customer_id, user_id, lines, drip_routes)   # v84: drip/injection lines recorded automatically
    if paid > 0:
        cur.execute("INSERT INTO sale_payments (sale_id, user_id, amount, method) VALUES (%s,%s,%s,%s)",
                    (sale_id, user_id, paid, payment))
    audit_fn(cur, 'sale.create', 'sale', sale_id, f"Total {total:.2f}, paid {paid:.2f}, discount {discount:.2f}",
             after={'total': total, 'subtotal': subtotal, 'discount': discount, 'tax': tax, 'paid': paid,
                    'payment': payment, 'customer_id': customer_id, 'prescription_id': rx_id,
                    'items': [{'medicine_id': mid, 'unit_price': price, 'batches': [[b, q] for b, q in parts]}
                              for mid, price, parts in lines]})
    if scheduled:                               # controlled-drug register: one row per batch part
        write_entries(cur, sale_id, user_id, customer_id, rx_id, entries_for_sale(lines, scheduled))
    return sale_id
