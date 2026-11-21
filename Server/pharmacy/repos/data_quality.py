"""SQL for the Data Quality report (v86.46). Read only. Deleted medicines are always left out."""

LIMIT = 200


def live_count(cur):
    cur.execute("SELECT COUNT(*) AS n FROM medicines WHERE is_deleted = 0")
    return int(cur.fetchone()['n'] or 0)


def duplicate_names(cur):
    cur.execute("""SELECT LOWER(TRIM(name)) AS key_name, COUNT(*) AS cnt,
                          GROUP_CONCAT(name SEPARATOR ' | ') AS names
                   FROM medicines WHERE is_deleted = 0
                   GROUP BY LOWER(TRIM(name)) HAVING COUNT(*) > 1
                   ORDER BY cnt DESC LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def missing_category(cur):
    cur.execute("""SELECT medicine_id, name FROM medicines
                   WHERE is_deleted = 0 AND category_id IS NULL ORDER BY name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def negative_stock(cur):
    """v86.66: stock below zero, usually an offline bill that was synced after the stock ran out."""
    cur.execute("""SELECT medicine_id, name, stock_quantity FROM medicines
                   WHERE is_deleted = 0 AND stock_quantity < 0 ORDER BY stock_quantity ASC, name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def missing_price(cur):
    cur.execute("""SELECT medicine_id, name, price FROM medicines
                   WHERE is_deleted = 0 AND (price IS NULL OR price <= 0) ORDER BY name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def missing_dosage_form(cur):
    cur.execute("""SELECT medicine_id, name FROM medicines
                   WHERE is_deleted = 0 AND (dosage_form IS NULL OR TRIM(dosage_form) = '')
                   ORDER BY name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def bad_strength(cur):
    # junk like "0", "-", "NA", or a bare number with no unit such as "500"
    cur.execute("""SELECT medicine_id, name, strength FROM medicines
                   WHERE is_deleted = 0 AND strength IS NOT NULL
                     AND (TRIM(strength) IN ('', '0', '-', 'NA', 'N/A', 'nil')
                          OR TRIM(strength) REGEXP '^[0-9.]+$')
                   ORDER BY name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def repeated_categories(cur):
    cur.execute("""SELECT LOWER(TRIM(category_name)) AS key_name, COUNT(*) AS cnt,
                          GROUP_CONCAT(category_name SEPARATOR ' | ') AS names
                   FROM categories GROUP BY LOWER(TRIM(category_name))
                   HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def stock_without_batch(cur):
    cur.execute("""SELECT m.medicine_id, m.name, m.stock_quantity FROM medicines m
                   WHERE m.is_deleted = 0 AND m.stock_quantity > 0
                     AND NOT EXISTS (SELECT 1 FROM batches b WHERE b.medicine_id = m.medicine_id AND b.quantity > 0)
                   ORDER BY m.name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def stock_batch_mismatch(cur):
    cur.execute("""SELECT m.medicine_id, m.name, m.stock_quantity, COALESCE(SUM(b.quantity), 0) AS batch_total
                   FROM medicines m LEFT JOIN batches b ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0
                   GROUP BY m.medicine_id, m.name, m.stock_quantity
                   HAVING m.stock_quantity <> COALESCE(SUM(b.quantity), 0)
                   ORDER BY m.name LIMIT %s""", (LIMIT,))
    return cur.fetchall()


def duplicate_barcodes(cur):
    """v86.55: one barcode on two or more live medicines (the database cannot enforce it, the unique index failed)."""
    cur.execute("""SELECT barcode, COUNT(*) AS cnt, GROUP_CONCAT(name SEPARATOR ' | ') AS names
                   FROM medicines WHERE is_deleted = 0 AND barcode IS NOT NULL AND TRIM(barcode) <> ''
                   GROUP BY barcode HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT %s""", (LIMIT,))
    return cur.fetchall()
