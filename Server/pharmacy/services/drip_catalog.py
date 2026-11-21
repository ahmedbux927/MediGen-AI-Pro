"""v85: drip and injection item list. Load a CSV catalog, add one item, or remove an item that has no history.

- The CSV is a product list (generic name, strength, dosage form, route, Rx flag). Price, stock and batches are
  not in it, so imported items start with price 0 and stock 0. Set the price in Medicines, and add stock by Purchase.
- Existing items (same name) are skipped, never changed.
- Only injection and infusion/IV-solution forms are accepted.
- Import is all-or-nothing: any bad row stops the whole file and nothing is written.
"""
import csv
import io

from pharmacy.services.drip_record import DRIP_FORMS

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 2000
MAX_NAME = 100
PLACEHOLDER_STRENGTHS = {'', 'product-specific', 'standard formulation', 'n/a', 'na', '-'}
FORM_MAP = {'injection': 'Injection', 'infusion / iv solution': 'Drip / IV fluid', 'infusion': 'Drip / IV fluid',
            'iv solution': 'Drip / IV fluid', 'drip / iv fluid': 'Drip / IV fluid'}


def _cell(row, key):
    return (row.get(key) or '').strip()


def map_form(text):
    """'Injection' -> 'Injection', 'Infusion / IV solution' -> 'Drip / IV fluid'. Anything else -> None."""
    low = (text or '').strip().lower()
    if low in FORM_MAP:
        return FORM_MAP[low]
    return None


def display_name(generic, strength):
    generic = generic.strip()
    if strength.strip().lower() in PLACEHOLDER_STRENGTHS or strength.strip().lower() in generic.lower():
        return generic[:MAX_NAME]
    return f"{generic} {strength.strip()}"[:MAX_NAME]


def parse_catalog(raw_bytes):
    """Returns (items, errors). Each item is a dict ready for import_items(). Stops at the first bad row."""
    if len(raw_bytes) > MAX_BYTES:
        return [], ['The file is larger than 2 MB.']
    try:
        text = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        return [], ['The file must be saved as UTF-8 CSV.']
    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or '').strip().lower() for h in (reader.fieldnames or [])}
    if not {'generic_name', 'dosage_form'} <= headers:
        return [], ['The CSV needs the columns generic_name and dosage_form.']
    items, seen = [], set()
    for line_no, row in enumerate(reader, start=2):
        row = {(k or '').strip().lower(): v for k, v in row.items()}
        if not any((v or '').strip() for v in row.values()):
            continue
        if len(items) >= MAX_ROWS:
            return [], [f'The file has more than {MAX_ROWS} rows. Split it into smaller files.']
        generic = _cell(row, 'generic_name')
        if not generic:
            return [], [f'Row {line_no}: generic_name is empty.']
        form = map_form(_cell(row, 'dosage_form'))
        if not form:
            return [], [f"Row {line_no} ({generic}): '{_cell(row, 'dosage_form')}' is not an injection or drip form."]
        strength = _cell(row, 'common_strength_or_concentration') or _cell(row, 'strength')
        name = display_name(generic, strength)
        if name.lower() in seen:
            continue                        # same name twice in the file: keep the first
        seen.add(name.lower())
        rx = _cell(row, 'prescription_required').lower()
        items.append({
            'name': name,
            'generic_name': generic[:100],
            'strength': strength[:100] or None,
            'dosage_form': form,
            'category': (_cell(row, 'category') or 'Injections')[:100],
            'rx_required': 1 if rx == 'yes' else 0,
            'product_code': _cell(row, 'product_id')[:50] or None,
        })
    if not items:
        return [], ['No item found in the file.']
    return items, []


def _category_id(cur, name):
    cur.execute("SELECT category_id FROM categories WHERE category_name=%s", (name,))
    row = cur.fetchone()
    if row:
        return row['category_id']
    cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (name,))
    return cur.lastrowid


def import_items(cur, items, user_id, source):
    """Writes the new items. Returns (added, skipped). The caller commits and writes the audit line."""
    added = skipped = 0
    for it in items:
        cur.execute("SELECT medicine_id FROM medicines WHERE name=%s", (it['name'],))
        if cur.fetchone():
            skipped += 1
            continue
        if it['dosage_form'] not in DRIP_FORMS:
            skipped += 1
            continue
        cid = _category_id(cur, it['category'])
        cur.execute("""INSERT INTO medicines (name, category_id, price, cost_price, stock_quantity, reorder_level,
                                             generic_name, strength, dosage_form, rx_required, product_code, import_source)
                       VALUES (%s,%s,0,0,0,0,%s,%s,%s,%s,%s,%s)""",
                    (it['name'], cid, it['generic_name'], it['strength'], it['dosage_form'], it['rx_required'],
                     it['product_code'], source[:100]))
        added += 1
    return added, skipped


def remove_blocker(cur, medicine_id):
    """Returns a reason text if the item has history (sales, stock, records), else None."""
    checks = [('sale_items', 'sales'), ('batches', 'stock batches'), ('stock_adjustments', 'stock history'),
              ('drip_injections', 'drip records')]
    for table, label in checks:
        try:
            cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE medicine_id=%s", (medicine_id,))
            if (cur.fetchone() or {}).get('n'):
                return f'It has {label}, so it cannot be deleted. Keep it with 0 stock, or leave it out of the list.'
        except Exception:
            return 'Could not check the item history. Nothing was deleted.'
    return None
