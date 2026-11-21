"""SQL for medicines, categories and stock adjustments."""
import math

LOW_FILTER = "(m.stock_quantity > 0 AND m.stock_quantity <= m.reorder_level)"
OUT_FILTER = "(m.stock_quantity <= 0)"
OK_FILTER = "(m.stock_quantity > m.reorder_level)"
MED_JOINS = """FROM medicines m
               LEFT JOIN categories c ON m.category_id = c.category_id"""


def list_medicines(cur, like, flt, page, per):
    """Return one page of medicines. `like` is a ready LIKE pattern or ''."""
    where, params = ["m.is_deleted = 0"], []
    if like:
        where.append("(m.name LIKE %s OR c.category_name LIKE %s)")
        params += [like, like]
    if flt == 'low':
        where.append(LOW_FILTER)
    elif flt == 'out':
        where.append(OUT_FILTER)
    elif flt == 'ok':
        where.append(OK_FILTER)
    wsql = (" WHERE " + " AND ".join(where)) if where else ""

    cur.execute("SELECT COUNT(*) AS total " + MED_JOINS + wsql, params)
    total = cur.fetchone()['total']
    pages = max(1, math.ceil(total / per))
    page = min(page, pages)
    offset = (page - 1) * per

    cur.execute("SELECT m.*, c.category_name " + MED_JOINS + wsql +
                " ORDER BY m.name ASC LIMIT %s OFFSET %s", params + [per, offset])
    return {'rows': cur.fetchall(), 'total': total, 'pages': pages,
            'page': page, 'offset': offset}


def medicine_stats(cur):
    cur.execute("""SELECT COUNT(*) AS total,
                          SUM(stock_quantity > 0) AS in_stock,
                          SUM(stock_quantity > 0 AND stock_quantity <= reorder_level) AS low,
                          SUM(stock_quantity <= 0) AS out_count
                   FROM medicines WHERE is_deleted = 0""")
    s = cur.fetchone()
    return {'total': int(s['total'] or 0), 'in_stock': int(s['in_stock'] or 0),
            'low': int(s['low'] or 0), 'empty': int(s['out_count'] or 0)}


def find_medicine_by_name(cur, name, exclude_id=None):
    """Case-insensitive name lookup. exclude_id skips one medicine (for edit)."""
    if exclude_id is None:
        cur.execute("SELECT medicine_id FROM medicines WHERE LOWER(name) = LOWER(%s)", (name,))
    else:
        cur.execute("SELECT medicine_id FROM medicines WHERE LOWER(name) = LOWER(%s) AND medicine_id <> %s",
                    (name, exclude_id))
    return cur.fetchone()


def insert_medicine(cur, data, stock):
    cur.execute("""INSERT INTO medicines (name, barcode, category_id, price, cost_price, stock_quantity, reorder_level, rack_location, dosage_form)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (data['name'], data.get('barcode'), data['category_id'], data['price'], data['cost'], stock, data['reorder'], data.get('rack_location'), data.get('dosage_form')))
    return cur.lastrowid


def update_medicine(cur, mid, data):
    cur.execute("""UPDATE medicines SET name=%s, barcode=%s, category_id=%s,
                          price=%s, cost_price=%s, reorder_level=%s, rack_location=%s, dosage_form=%s WHERE medicine_id=%s""",
                (data['name'], data.get('barcode'), data['category_id'], data['price'], data['cost'], data['reorder'], data.get('rack_location'), data.get('dosage_form'), mid))


def barcode_map(cur):
    """v86.35: {barcode: name} for every live medicine that has a barcode."""
    cur.execute("SELECT barcode, name FROM medicines WHERE barcode IS NOT NULL AND barcode <> '' AND is_deleted = 0")
    return {r['barcode']: r['name'] for r in cur.fetchall()}


def find_medicine_by_barcode(cur, code, exclude_id=None):
    if exclude_id is None:
        cur.execute("SELECT medicine_id, name FROM medicines WHERE barcode = %s AND is_deleted = 0", (code,))
    else:
        cur.execute("SELECT medicine_id, name FROM medicines WHERE barcode = %s AND medicine_id <> %s", (code, exclude_id))
    return cur.fetchone()


def lock_medicine(cur, mid):
    """Read name and stock with a row lock (FOR UPDATE)."""
    cur.execute("SELECT name, stock_quantity FROM medicines WHERE medicine_id=%s FOR UPDATE", (mid,))
    return cur.fetchone()


def take_from_batches_fifo(cur, mid, qty):
    """Remove qty units from batches, oldest expiry first. Caller checked stock first."""
    remaining = qty
    cur.execute("""SELECT batch_id, quantity FROM batches WHERE medicine_id=%s AND quantity > 0
                   ORDER BY expiry_date ASC, batch_id ASC FOR UPDATE""", (mid,))
    for b in cur.fetchall():
        if remaining <= 0:
            break
        take = min(b['quantity'], remaining)
        cur.execute("UPDATE batches SET quantity = quantity - %s WHERE batch_id=%s", (take, b['batch_id']))
        remaining -= take


def set_stock(cur, mid, new):
    cur.execute("UPDATE medicines SET stock_quantity=%s WHERE medicine_id=%s", (new, mid))


def insert_adjustment(cur, mid, user_id, change, old, new, reason, note):
    cur.execute("""INSERT INTO stock_adjustments (medicine_id, user_id, change_qty, old_stock, new_stock, reason, note)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (mid, user_id, change, old, new, reason, note))


def insert_opening_stock(cur, mid, user_id, stock):
    cur.execute("""INSERT INTO stock_adjustments (medicine_id, user_id, change_qty, old_stock, new_stock, reason, note)
                   VALUES (%s,%s,%s,0,%s,'Opening stock','Added with new medicine')""",
                (mid, user_id, stock, stock))


def stock_history(cur, mid, limit=15):
    cur.execute("""SELECT a.created_at, a.change_qty, a.old_stock, a.new_stock, a.reason, a.note, u.full_name
                   FROM stock_adjustments a LEFT JOIN users u ON a.user_id = u.user_id
                   WHERE a.medicine_id=%s ORDER BY a.adjustment_id DESC LIMIT %s""", (mid, limit))
    return cur.fetchall()


def delete_medicine(cur, mid):
    cur.execute("DELETE FROM medicines WHERE medicine_id=%s", (mid,))


def export_medicine_rows(cur, ids):
    """All medicines, or only the ids given (list of ints)."""
    sql = """SELECT m.name, c.category_name, m.price, m.cost_price,
                    m.stock_quantity, m.reorder_level
             FROM medicines m
             LEFT JOIN categories c ON m.category_id = c.category_id"""
    params = []
    if ids:
        sql += " WHERE m.is_deleted = 0 AND m.medicine_id IN (" + ",".join(["%s"] * len(ids)) + ")"
        params = list(ids)
    else:
        sql += " WHERE m.is_deleted = 0"   # v86.37: hidden medicines are not exported
    sql += " ORDER BY m.name"
    cur.execute(sql, params)
    return cur.fetchall()


def list_categories_by_name(cur):
    cur.execute("SELECT * FROM categories ORDER BY category_name")
    return cur.fetchall()


HISTORY_TABLES = (('sale_items', 'sales'), ('purchase_items', 'purchases'),
                  ('prescription_items', 'prescriptions'), ('drip_injections', 'drip records'))


def history_blocker(cur, mid):
    """v86.27: sales, purchases, prescriptions and drip records keep a medicine. Returns a reason or None."""
    for table, label in HISTORY_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE medicine_id=%s", (mid,))
            if (cur.fetchone() or {}).get('n'):
                return f"has {label}, so it cannot be deleted."
        except Exception as e:
            if e.args and e.args[0] == 1146:       # table not in this database: no history there
                continue
            raise
    return None


def purge_medicine(cur, mid):
    """v86.29: 'delete' hides the medicine. It is renamed so the name and barcode are free again,
    and its sales, purchases and bills keep their rows (the bills show the old name with '(deleted)')."""
    cur.execute("""UPDATE medicines SET is_deleted = 1, barcode = NULL,
                   name = LEFT(CONCAT(name, ' (deleted ', medicine_id, ')'), 100)
                   WHERE medicine_id = %s""", (mid,))


def bulk_update_fields(cur, ids, category_id=None, dosage_form=None, price=None, strength=None):
    """v86.45: change only the fields that were filled in, for every given medicine."""
    sets, params = [], []
    if category_id is not None:
        sets.append("category_id = %s"); params.append(category_id)
    if dosage_form is not None:
        sets.append("dosage_form = %s"); params.append(dosage_form)
    if price is not None:
        sets.append("price = %s"); params.append(price)
    if strength is not None:
        sets.append("strength = %s"); params.append(strength)
    if not sets or not ids:
        return 0
    marks = ",".join(["%s"] * len(ids))
    cur.execute(f"UPDATE medicines SET {', '.join(sets)} WHERE is_deleted = 0 AND medicine_id IN ({marks})",
                params + list(ids))
    return cur.rowcount


def bulk_update_expiry(cur, ids, expiry):
    """v86.45: sets the expiry on every batch of the given medicines.
    A medicine with stock but no batch gets an 'OPENING' batch that holds its current stock, so the expiry shows.
    A medicine with no stock and no batch cannot have an expiry yet (it is set when stock is received).
    Returns {'updated': batches changed, 'created': opening batches made, 'skipped': items left alone}."""
    if not ids:
        return {'updated': 0, 'created': 0, 'skipped': 0}
    marks = ",".join(["%s"] * len(ids))
    cur.execute(f"SELECT medicine_id, stock_quantity FROM medicines WHERE medicine_id IN ({marks})", list(ids))
    stock = {r['medicine_id']: int(r['stock_quantity'] or 0) for r in cur.fetchall()}
    cur.execute(f"SELECT DISTINCT medicine_id FROM batches WHERE quantity > 0 AND medicine_id IN ({marks})", list(ids))
    with_stock_batch = {r['medicine_id'] for r in cur.fetchall()}
    cur.execute(f"UPDATE batches SET expiry_date = %s WHERE medicine_id IN ({marks})", [expiry] + list(ids))
    updated = cur.rowcount
    created = skipped = 0
    for mid in ids:
        if mid in with_stock_batch:
            continue
        qty = stock.get(mid, 0)
        if qty > 0:
            cur.execute("""INSERT INTO batches (medicine_id, batch_number, expiry_date, quantity, purchase_price)
                           VALUES (%s,'OPENING',%s,%s,NULL)""", (mid, expiry, qty))
            created += 1
        else:
            skipped += 1
    return {'updated': updated, 'created': created, 'skipped': skipped}


def find_same_product(cur, name, strength=None, exclude_id=None):
    """v86.54: a live medicine with the same name AND the same strength (blank strength counts as blank).
    Same name with a different strength is allowed (Panadol 500 and Panadol 120 are different products).
    Deleted (hidden) medicines do not count."""
    sql = """SELECT medicine_id, name, strength FROM medicines
             WHERE is_deleted = 0 AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
               AND LOWER(TRIM(COALESCE(strength, ''))) = LOWER(TRIM(%s))"""
    params = [name or '', strength or '']
    if exclude_id is not None:
        sql += " AND medicine_id <> %s"
        params.append(exclude_id)
    cur.execute(sql + " LIMIT 1", params)
    return cur.fetchone()


def duplicate_message(name, strength=None):
    label = f"{name} {strength}".strip() if strength else name
    return (f"Duplicate: '{label}' already exists (same name and strength). "
            "The new entry was not saved. Please edit the existing entry above.")
