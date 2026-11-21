"""Purchase drafts (v87.05). A draft is a suggested order for staff to review and send to the supplier.
A draft NEVER changes stock: stock changes only when the purchase is received on the Purchase page.

Rules:
- Drafts come from the purchase suggestions (items low or running out in 14 days).
- A medicine already on an open draft is not added again.
- One draft is made per supplier. Items with no supplier history go to one draft with no supplier.
- A quantity of 0 removes the line. Sent or cancelled drafts cannot be edited.
"""
from collections import OrderedDict

MAX_QTY = 100000


class DraftError(ValueError):
    """A problem the user can fix. The message is shown as it is."""


def parse_qty(text):
    try:
        q = int(str(text).strip())
    except (TypeError, ValueError):
        raise DraftError('Quantity must be a whole number.')
    if q < 0 or q > MAX_QTY:
        raise DraftError(f'Quantity must be from 0 to {MAX_QTY:,}.')
    return q


def group_by_supplier(rows, supplier_of):
    """rows: dicts with medicine_id, name, qty, cost. Returns {supplier_id or None: [lines]}, supplier-named first."""
    groups = OrderedDict()
    for r in rows:
        groups.setdefault(supplier_of.get(r['medicine_id']), []).append(r)
    return groups


def lines_total(lines):
    return round(sum(float(l['quantity']) * float(l['unit_cost'] or 0) for l in lines), 2)


def open_medicine_ids(cur):
    cur.execute("""SELECT DISTINCT l.medicine_id FROM purchase_draft_lines l
                   JOIN purchase_drafts d ON d.draft_id = l.draft_id WHERE d.status = 'draft'""")
    return {r['medicine_id'] for r in cur.fetchall()}


def last_supplier_map(cur):
    """{medicine_id: supplier_id} from the most recent purchase order that included each medicine."""
    cur.execute("""SELECT pi.medicine_id, po.supplier_id
                   FROM purchase_items pi JOIN purchase_orders po ON po.po_id = pi.po_id
                   JOIN (SELECT pi2.medicine_id, MAX(po2.po_id) AS last_po
                         FROM purchase_items pi2 JOIN purchase_orders po2 ON po2.po_id = pi2.po_id
                         GROUP BY pi2.medicine_id) x
                     ON x.medicine_id = pi.medicine_id AND x.last_po = po.po_id""")
    return {r['medicine_id']: r['supplier_id'] for r in cur.fetchall()}


def create_from_suggestions(cur, user_id, suggestion_rows):
    """Writes one draft per supplier from the suggestion rows. Returns the number of drafts and lines written."""
    skip = open_medicine_ids(cur)
    fresh = [r for r in suggestion_rows if r['medicine_id'] not in skip and r['qty'] > 0]
    groups = group_by_supplier(fresh, last_supplier_map(cur))
    drafts = lines = 0
    for supplier_id, items in groups.items():
        cur.execute("INSERT INTO purchase_drafts (supplier_id, status, created_by) VALUES (%s, 'draft', %s)",
                    (supplier_id, user_id))
        draft_id = cur.lastrowid
        drafts += 1
        for r in items:
            cur.execute("""INSERT INTO purchase_draft_lines (draft_id, medicine_id, quantity, unit_cost)
                           VALUES (%s, %s, %s, %s)""", (draft_id, r['medicine_id'], r['qty'], r['cost']))
            lines += 1
    return drafts, lines


def apply_quantities(cur, draft_id, pairs):
    """pairs: [(medicine_id, quantity)]. Quantity 0 removes the line."""
    for mid, qty in pairs:
        if qty == 0:
            cur.execute("DELETE FROM purchase_draft_lines WHERE draft_id = %s AND medicine_id = %s", (draft_id, mid))
        else:
            cur.execute("UPDATE purchase_draft_lines SET quantity = %s WHERE draft_id = %s AND medicine_id = %s",
                        (qty, draft_id, mid))
