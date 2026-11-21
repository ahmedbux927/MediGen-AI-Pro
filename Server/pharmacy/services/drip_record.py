"""Drip and injection record (v77). Pure rules + one table helper. No Flask.

- Only medicines whose dosage form is an injection or drip can be recorded here.
- Stock is taken oldest-expiry first (done by the caller, same as stock adjust).
- Each record keeps who gave it, when, to which patient, the route, the dose text and the quantity.
- Nothing here decides a dose. The dose text is typed by the staff member, from the doctor's order.
"""
import re

ROUTES = ['Not set', 'IV drip', 'IV injection', 'IM injection', 'SC injection']
AUTO_ROUTE = 'Not set'      # sales do not ask for the route: staff set it later if needed
DRIP_FORMS = ['Injection', 'Drip / IV fluid']
_DRIP_WORDS = re.compile(r'\b(inj|injection|injectable|drip|iv|infusion)\b', re.IGNORECASE)
MAX_QTY = 50
_table_ready = False


def is_drip_form(dosage_form):
    """True for injection / drip forms (also works for older text such as 'injection 2ml')."""
    return bool(_DRIP_WORDS.search(dosage_form or ''))


def read_record(form):
    """Check the form. Returns a clean dict or raises ValueError with a message for the user."""
    try:
        medicine_id = int((form.get('medicine_id') or '').strip())
    except ValueError:
        raise ValueError('Please choose a medicine.')
    raw_customer = (form.get('customer_id') or '').strip()
    if raw_customer:
        try:
            customer_id = int(raw_customer)
        except ValueError:
            raise ValueError('Please choose the patient.')
    else:
        customer_id = None                       # walk-in: allowed
    route = (form.get('route') or AUTO_ROUTE).strip()
    if route not in ROUTES:
        raise ValueError('Please choose how it was given (IV drip, IV or IM or SC injection).')
    dose = (form.get('dose_text') or '').strip()
    if not dose:
        raise ValueError('Please enter the dose, for example "1 vial 2 ml" or "500 ml over 2 hours".')
    if len(dose) > 100:
        raise ValueError('The dose text is too long (100 characters at most).')
    try:
        qty = int((form.get('quantity') or '1').strip())
    except ValueError:
        raise ValueError('Quantity must be a whole number.')
    if not 1 <= qty <= MAX_QTY:
        raise ValueError(f'Quantity must be between 1 and {MAX_QTY}.')
    notes = (form.get('notes') or '').strip()[:255] or None
    return {'medicine_id': medicine_id, 'customer_id': customer_id, 'route': route,
            'dose_text': dose, 'quantity': qty, 'notes': notes}


def auto_record_sale(cur, sale_id, customer_id, user_id, lines, routes=None):
    """Called from the sale itself (counter and POS). Every drip or injection line gets a record, no extra form.
    lines = [(medicine_id, unit_price, [(batch_id, qty), ...]), ...]. Stock was already taken by the sale.
    routes = {medicine_id: route} chosen on the sale screen (optional). Unknown or missing = AUTO_ROUTE.
    Returns how many records were written."""
    mids = sorted({mid for mid, _, _ in lines})
    if not mids:
        return 0
    cur.execute("SELECT medicine_id, dosage_form, strength FROM medicines WHERE medicine_id IN (%s)" % ','.join(['%s'] * len(mids)),
                tuple(mids))
    info = {r['medicine_id']: r for r in cur.fetchall()}
    rows = []
    for mid, _price, parts in lines:
        m = info.get(mid)
        if not m or not is_drip_form(m['dosage_form']):
            continue
        qty = int(sum(take for _, take in parts))
        dose = (m.get('strength') or 'as ordered').strip()[:100]
        route = (routes or {}).get(mid, AUTO_ROUTE)
        if route not in ROUTES:
            route = AUTO_ROUTE
        rows.append((mid, customer_id, route, dose, qty, sale_id, f'From sale #{sale_id}', user_id))
    if not rows:
        return 0
    # B1 fix: no CREATE/ALTER here. MySQL DDL commits the open sale transaction, so a later
    # error could leave a half-saved sale with stock already taken. The table is created at startup (app.py).
    for row in rows:
        cur.execute("""INSERT INTO drip_injections (medicine_id, customer_id, route, dose_text, quantity, sale_id, notes, given_by)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", row)
    return len(rows)


def ensure_drip_table(cur):
    """Create the record table once (safe to run many times)."""
    global _table_ready
    if _table_ready:
        return
    cur.execute("""CREATE TABLE IF NOT EXISTS drip_injections (
        record_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        medicine_id INT NOT NULL,
        customer_id INT NULL,
        route VARCHAR(20) NOT NULL,
        dose_text VARCHAR(100) NOT NULL,
        quantity INT NOT NULL,
        sale_id INT NULL,
        notes VARCHAR(255) NULL,
        given_by INT NOT NULL,
        given_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_drip_day (given_at),
        KEY idx_drip_customer (customer_id),
        KEY idx_drip_sale (sale_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    _upgrade_table(cur)
    _table_ready = True


def _column(cur, name):
    cur.execute("""SELECT IS_NULLABLE FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'drip_injections' AND COLUMN_NAME = %s""", (name,))
    return cur.fetchone()


def _upgrade_table(cur):
    """v84: a table made by v77 has no sale_id and customer_id must be optional. CREATE TABLE IF NOT EXISTS does not change it,
    so add the missing parts here. Safe to run many times."""
    if not _column(cur, 'sale_id'):
        cur.execute("ALTER TABLE drip_injections ADD COLUMN sale_id INT NULL")
        cur.execute("ALTER TABLE drip_injections ADD KEY idx_drip_sale (sale_id)")
    col = _column(cur, 'customer_id')
    if col and col['IS_NULLABLE'] == 'NO':
        cur.execute("ALTER TABLE drip_injections MODIFY customer_id INT NULL")

