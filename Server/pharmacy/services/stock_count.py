"""Stock count with variance approval (Phase 3, backend). Rules are pure; the functions with a cursor
write the database and leave the commit to the caller.

Life of a count:  open -> submitted -> approved (Admin only)
                  open -> cancelled     submitted -> open (send back to counting)
- Only one count can be open at a time.
- Start: every medicine's current stock is saved as system_qty.
- While open: counted quantities can be entered and changed.
- Submit: every line must have a counted quantity.
- Approve: refused if stock changed after the start for any counted line (sales during the count).
  Otherwise each changed medicine gets its stock set to the counted quantity, one stock_adjustments row
  and one audit row per medicine. Batches are NOT changed here; use the existing batch sync tool afterwards.
"""

TRANSITIONS = {'open': {'submitted', 'cancelled'}, 'submitted': {'approved', 'open'},
               'approved': set(), 'cancelled': set()}


class CountError(ValueError):
    """A problem the user can fix. The message is shown as it is."""


def can_move(state, new_state):
    return new_state in TRANSITIONS.get(state, set())


def variance(system_qty, counted_qty):
    return counted_qty - system_qty


def summarise(lines, cost_by_medicine):
    """lines: dicts with medicine_id, system_qty, counted_qty. Returns totals for the approver to read."""
    counted = [l for l in lines if l['counted_qty'] is not None]
    changed = [l for l in counted if variance(l['system_qty'], l['counted_qty']) != 0]
    value = sum(variance(l['system_qty'], l['counted_qty']) * float(cost_by_medicine.get(l['medicine_id'], 0) or 0)
                for l in changed)
    return {'lines': len(lines), 'counted': len(counted), 'uncounted': len(lines) - len(counted),
            'changed': len(changed),
            'short_units': sum(-variance(l['system_qty'], l['counted_qty']) for l in changed if variance(l['system_qty'], l['counted_qty']) < 0),
            'over_units': sum(variance(l['system_qty'], l['counted_qty']) for l in changed if variance(l['system_qty'], l['counted_qty']) > 0),
            'value_change': round(value, 2)}


def conflicts(lines, current_stock):
    """Medicine ids whose stock changed since the count started (only lines that have a counted quantity)."""
    return [l['medicine_id'] for l in lines
            if l['counted_qty'] is not None and current_stock.get(l['medicine_id']) != l['system_qty']]


def _open_count(cur):
    cur.execute("SELECT count_id, status FROM stock_counts WHERE status IN ('open','submitted') ORDER BY count_id DESC LIMIT 1")
    return cur.fetchone()


def start_count(cur, user_id, note=''):
    if _open_count(cur):
        raise CountError('A stock count is already in progress. Finish or cancel it first.')
    cur.execute("INSERT INTO stock_counts (status, started_by, note) VALUES ('open', %s, %s)", (user_id, note or None))
    count_id = cur.lastrowid
    cur.execute("SELECT medicine_id, stock_quantity FROM medicines WHERE is_deleted = 0")
    for r in cur.fetchall():
        cur.execute("INSERT INTO stock_count_lines (count_id, medicine_id, system_qty) VALUES (%s,%s,%s)",
                    (count_id, r['medicine_id'], r['stock_quantity'] or 0))
    return count_id


def _status(cur, count_id):
    cur.execute("SELECT status FROM stock_counts WHERE count_id=%s", (count_id,))
    row = cur.fetchone()
    if not row:
        raise CountError('Stock count not found.')
    return row['status']


def record_count(cur, count_id, medicine_id, counted_qty, user_id):
    if _status(cur, count_id) != 'open':
        raise CountError('This count is not open for counting.')
    try:
        counted_qty = int(counted_qty)
    except (TypeError, ValueError):
        raise CountError('Counted quantity must be a whole number.')
    if counted_qty < 0 or counted_qty > 1000000:
        raise CountError('Counted quantity must be a whole number from 0 to 1,000,000.')
    cur.execute("""UPDATE stock_count_lines SET counted_qty=%s, counted_by=%s, counted_at=NOW()
                   WHERE count_id=%s AND medicine_id=%s""", (counted_qty, user_id, count_id, medicine_id))
    if cur.rowcount == 0:
        raise CountError('This medicine is not part of the count.')


def submit_count(cur, count_id):
    if not can_move(_status(cur, count_id), 'submitted'):
        raise CountError('Only an open count can be submitted.')
    cur.execute("SELECT COUNT(*) AS n FROM stock_count_lines WHERE count_id=%s AND counted_qty IS NULL", (count_id,))
    left = cur.fetchone()['n']
    if left:
        raise CountError(f'{left} medicine(s) are not counted yet. Count them all before submitting.')
    cur.execute("UPDATE stock_counts SET status='submitted', submitted_at=NOW() WHERE count_id=%s", (count_id,))


def cancel_count(cur, count_id):
    if not can_move(_status(cur, count_id), 'cancelled'):
        raise CountError('Only an open count can be cancelled.')
    cur.execute("UPDATE stock_counts SET status='cancelled' WHERE count_id=%s", (count_id,))


def approve_count(cur, count_id, approver_id, approver_role, audit_fn):
    """Apply the counted quantities. Admin only. Returns the number of medicines changed."""
    if approver_role != 'Admin':
        raise CountError('Only an Admin can approve a stock count.')
    if not can_move(_status(cur, count_id), 'approved'):
        raise CountError('Only a submitted count can be approved. Submit it first.')
    cur.execute("""SELECT l.medicine_id, l.system_qty, l.counted_qty, m.name, m.stock_quantity
                   FROM stock_count_lines l JOIN medicines m ON m.medicine_id = l.medicine_id
                   WHERE l.count_id=%s""", (count_id,))
    lines = cur.fetchall()
    current = {l['medicine_id']: l['stock_quantity'] or 0 for l in lines}
    clash = conflicts(lines, current)
    if clash:
        raise CountError(f'Stock changed during the count for {len(clash)} medicine(s) (for example a sale). '
                         'Cancel this count and start again.')
    changed = 0
    for l in lines:
        if l['counted_qty'] is None:
            continue
        diff = variance(l['system_qty'], l['counted_qty'])
        if diff == 0:
            continue
        cur.execute("UPDATE medicines SET stock_quantity=%s WHERE medicine_id=%s", (l['counted_qty'], l['medicine_id']))
        cur.execute("""INSERT INTO stock_adjustments (medicine_id, user_id, change_qty, old_stock, new_stock, reason, note)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (l['medicine_id'], approver_id, diff, l['system_qty'], l['counted_qty'], 'Stock count',
                     f'Count #{count_id}'))
        audit_fn(cur, 'stock.count_approved', 'medicine', l['medicine_id'],
                 f"Count #{count_id}: {l['name']} {l['system_qty']} -> {l['counted_qty']}",
                 after={'count_id': count_id, 'old': l['system_qty'], 'new': l['counted_qty']})
        changed += 1
    cur.execute("UPDATE stock_counts SET status='approved', approved_by=%s, approved_at=NOW() WHERE count_id=%s",
                (approver_id, count_id))
    return changed


def reopen_count(cur, count_id):
    """Send a submitted count back to counting (lines and counted quantities are kept)."""
    if not can_move(_status(cur, count_id), 'open'):
        raise CountError('Only a submitted count can be sent back to counting.')
    cur.execute("UPDATE stock_counts SET status='open', submitted_at=NULL WHERE count_id=%s", (count_id,))
