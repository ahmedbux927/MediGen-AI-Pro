"""Controlled-drug register and the prescription rule for scheduled medicines (compliance, Phase 4 backend).

IMPORTANT: which medicines are controlled, the exact register format, and what buyer details must be kept
are rules set by the Pakistan Pharmacy Council and the provincial drug authority. They are NOT confirmed here.
This module only enforces what the pharmacist sets: a medicine with a schedule value (medicines.schedule)
- is written to the register on every sale, and
- cannot be sold without a prescription attached to the bill.
Confirm the rules with the authority before relying on this for compliance.
"""

REGISTER_TRIGGERS = [
    ('trg_register_no_update', "CREATE TRIGGER trg_register_no_update BEFORE UPDATE ON controlled_register FOR EACH ROW "
                               "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Controlled register is append-only: updates are not allowed'"),
    ('trg_register_no_delete', "CREATE TRIGGER trg_register_no_delete BEFORE DELETE ON controlled_register FOR EACH ROW "
                               "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Controlled register is append-only: deletes are not allowed'"),
]


def ensure_register_triggers(cur, logger=None):
    """Append-only protection. Needs the TRIGGER permission; the app still starts without it (a warning is logged)."""
    try:
        for name, ddl in REGISTER_TRIGGERS:
            cur.execute(f"DROP TRIGGER IF EXISTS {name}")
            cur.execute(ddl)
    except Exception:
        if logger:
            logger.warning('controlled register triggers not created (needs TRIGGER permission)', exc_info=True)


def scheduled_items(cur, medicine_ids):
    """{medicine_id: schedule} for the medicines that have a schedule set."""
    ids = [int(m) for m in medicine_ids]
    if not ids:
        return {}
    placeholders = ','.join(['%s'] * len(ids))
    cur.execute(f"SELECT medicine_id, name, schedule FROM medicines WHERE medicine_id IN ({placeholders})", ids)
    return {r['medicine_id']: (r['schedule'], r['name']) for r in cur.fetchall() if r.get('schedule')}


def prescription_missing(scheduled, rx_id):
    """Names of scheduled medicines when the bill has no prescription. Empty list = fine."""
    if rx_id or not scheduled:
        return []
    return [name for _, name in scheduled.values()]


def entries_for_sale(lines, scheduled):
    """lines = [(medicine_id, unit_price, [(batch_id, qty)])] from the sale. One entry per batch part."""
    out = []
    for mid, _price, parts in lines:
        if mid in scheduled:
            schedule = scheduled[mid][0]
            for batch_id, qty in parts:
                out.append({'medicine_id': mid, 'schedule': schedule, 'batch_id': batch_id, 'quantity': qty})
    return out


def write_entries(cur, sale_id, user_id, customer_id, rx_id, entries):
    for e in entries:
        cur.execute("""INSERT INTO controlled_register (sale_id, medicine_id, schedule, batch_id, quantity,
                                                        customer_id, prescription_id, user_id)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (sale_id, e['medicine_id'], e['schedule'], e['batch_id'], e['quantity'],
                     customer_id, rx_id, user_id))
    return len(entries)


MAX_RANGE_DAYS = 366


class RegisterError(ValueError):
    """A problem the user can fix. The message is shown as it is."""


def parse_range(start_text, end_text, today):
    """Dates as YYYY-MM-DD. Empty start = 30 days before end; empty end = today. Returns (start, end)."""
    from datetime import date, timedelta
    try:
        end = date.fromisoformat(end_text) if end_text else today
        start = date.fromisoformat(start_text) if start_text else end - timedelta(days=30)
    except ValueError:
        raise RegisterError('Date must be in the form YYYY-MM-DD.')
    if start > end:
        raise RegisterError('The start date is after the end date.')
    if (end - start).days > MAX_RANGE_DAYS:
        raise RegisterError('Please choose a period of one year or less.')
    return start, end


def summarise_entries(rows):
    """rows: dicts with medicine_name, schedule, quantity. Returns one line per medicine, largest quantity first."""
    totals = {}
    for r in rows:
        key = (r['medicine_name'], r['schedule'])
        t = totals.setdefault(key, {'medicine_name': key[0], 'schedule': key[1], 'entries': 0, 'quantity': 0})
        t['entries'] += 1
        t['quantity'] += int(r['quantity'] or 0)
    return sorted(totals.values(), key=lambda t: (-t['quantity'], t['medicine_name']))
