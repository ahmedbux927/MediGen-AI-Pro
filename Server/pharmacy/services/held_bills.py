"""Hold and resume bills (Phase 2). Pure rules + a few statements with a cursor. The caller commits.

- A held bill keeps the medicines and quantities, the customer and a note, as JSON.
- Holding does not reserve stock. Completing the resumed bill runs the normal stock check.
- At most MAX_OPEN_PER_COUNTER open holds per counter.
- Holds older than HOLD_HOURS are marked expired (run expire_old_holds from the daily job).
"""
import json

MAX_OPEN_PER_COUNTER = 10
MAX_COUNTERS = 20
HOLD_HOURS = 24
MAX_LINES = 100


class HoldError(ValueError):
    """A problem the cashier can fix. The message is shown as it is."""


def _payload(customer_id, wanted, note):
    return json.dumps({'customer_id': customer_id,
                       'lines': [{'medicine_id': int(m), 'quantity': int(q)} for m, q in sorted(wanted.items())],
                       'note': (note or '')[:200]}, separators=(',', ':'))


def hold_bill(cur, user_id, counter_no, customer_id, wanted, note=''):
    if not 1 <= int(counter_no) <= MAX_COUNTERS:
        raise HoldError(f'Counter must be a number from 1 to {MAX_COUNTERS}.')
    if not wanted:
        raise HoldError('Nothing to hold: add at least one medicine first.')
    if len(wanted) > MAX_LINES:
        raise HoldError(f'A bill can have at most {MAX_LINES} different medicines.')
    cur.execute("SELECT COUNT(*) AS n FROM held_bills WHERE status='open' AND counter_no=%s", (counter_no,))
    if cur.fetchone()['n'] >= MAX_OPEN_PER_COUNTER:
        raise HoldError(f'Counter {counter_no} already has {MAX_OPEN_PER_COUNTER} held bills. Resume or discard one first.')
    cur.execute("INSERT INTO held_bills (counter_no, user_id, customer_id, payload) VALUES (%s,%s,%s,%s)",
                (counter_no, user_id, customer_id or None, _payload(customer_id, wanted, note)))
    return cur.lastrowid


def open_holds(cur, counter_no=None):
    if counter_no is None:
        cur.execute("""SELECT hold_id, counter_no, customer_id, created_at FROM held_bills
                       WHERE status='open' ORDER BY counter_no, hold_id""")
    else:
        cur.execute("""SELECT hold_id, counter_no, customer_id, created_at FROM held_bills
                       WHERE status='open' AND counter_no=%s ORDER BY hold_id""", (counter_no,))
    return cur.fetchall()


def resume_hold(cur, hold_id):
    """Returns the saved bill as a dict and marks it resumed. A hold can be resumed only once."""
    cur.execute("SELECT hold_id, status, payload FROM held_bills WHERE hold_id=%s FOR UPDATE", (hold_id,))
    row = cur.fetchone()
    if not row:
        raise HoldError('That held bill was not found.')
    if row['status'] != 'open':
        raise HoldError(f"That held bill is already {row['status']}.")
    cur.execute("UPDATE held_bills SET status='resumed', closed_at=NOW() WHERE hold_id=%s", (hold_id,))
    return json.loads(row['payload'])


def discard_hold(cur, hold_id):
    cur.execute("SELECT status FROM held_bills WHERE hold_id=%s", (hold_id,))
    row = cur.fetchone()
    if not row:
        raise HoldError('That held bill was not found.')
    if row['status'] != 'open':
        raise HoldError(f"That held bill is already {row['status']}.")
    cur.execute("UPDATE held_bills SET status='discarded', closed_at=NOW() WHERE hold_id=%s", (hold_id,))


def expire_old_holds(cur, hours=HOLD_HOURS):
    cur.execute("""UPDATE held_bills SET status='expired', closed_at=NOW()
                   WHERE status='open' AND created_at < NOW() - INTERVAL %s HOUR""", (int(hours),))
    return cur.rowcount
