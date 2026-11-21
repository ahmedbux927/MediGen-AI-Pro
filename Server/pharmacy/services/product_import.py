"""Product import (backend track, Phase 1).

Reads a product list (CSV or XLSX), checks every row, shows a plan, and writes it in ONE transaction.

Rules that matter for a pharmacy:
- Nothing is written unless every row is valid (a dry run is the default in the script).
- Placeholders such as "Verify brand / pack" or "N/A" are stored as NULL (unknown), never as real data.
- Prescription flag: "Yes" -> 1, "No" -> 0, anything else (for example "Check local rules") -> NULL = unknown.
  An unknown Rx flag must be confirmed by the pharmacist. The import never guesses "No".
- Stock on an EXISTING medicine is never changed by an import (stock changes go through the audited
  stock adjustment). Only NEW medicines get their opening stock, as one batch.
- Every created medicine gets an audit row.

The pure functions take plain values and a date, so they are tested without MySQL.
apply_plan() takes a DB cursor; the caller owns the commit/rollback.
"""
import csv
import io
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

CANON_COLUMNS = ['product_code', 'name', 'barcode', 'category', 'generic_name', 'manufacturer', 'strength',
                 'dosage_form', 'purchase_price', 'selling_price', 'stock_quantity', 'minimum_stock',
                 'batch_number', 'manufacturing_date', 'expiry_date', 'supplier', 'rx_required']
REQUIRED_COLUMNS = ['name', 'selling_price']
# Aliases accepted in the header row (lower case, spaces turned into underscores)
HEADER_ALIASES = {'product_name': 'name', 'item': 'name', 'medicine': 'name', 'code': 'product_code',
                  'price': 'selling_price', 'sale_price': 'selling_price', 'cost': 'purchase_price',
                  'cost_price': 'purchase_price', 'qty': 'stock_quantity', 'stock': 'stock_quantity',
                  'reorder_level': 'minimum_stock', 'batch': 'batch_number', 'expiry': 'expiry_date',
                  'rx': 'rx_required', 'prescription_required': 'rx_required'}
PLACEHOLDERS = {'', 'n/a', 'na', '-', 'tbd', 'unknown', 'null', 'none'}
EXPIRY_WARN_DAYS = 30
DEFAULT_REORDER = 20
MAX_NAME = 100
MAX_BARCODE = 64
MAX_BATCH = 50


# ---------- cell parsing (pure) ----------

def clean(value):
    """Return the trimmed text, or None for empty cells and placeholder text such as 'Verify brand'."""
    if value is None:
        return None
    s = str(value).strip()
    low = s.lower()
    if low in PLACEHOLDERS or low.startswith('verify'):
        return None
    return s


def money(value):
    s = clean(value)
    if s is None:
        return None
    s = re.sub(r'(?i)\bpkr\b|\brs\.?', '', s).replace(',', '').strip()
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError(f'not a price: {value!r}')
    if d < 0:
        raise ValueError('a price cannot be negative')
    return d.quantize(Decimal('0.01'))


def whole_number(value, name):
    s = clean(value)
    if s is None:
        return None
    s = s[:-2] if s.endswith('.0') else s
    if not s.isdigit():
        raise ValueError(f'{name} must be a whole number: {value!r}')
    return int(s)


def barcode_of(value):
    s = clean(value)
    if s is None:
        return None
    s = re.sub(r'\s+', '', s)
    if s.endswith('.0'):                      # Excel stores numbers as floats
        s = s[:-2]
    if not s.isdigit():
        raise ValueError(f'barcode must contain digits only: {value!r}')
    if len(s) > MAX_BARCODE:
        raise ValueError('barcode is too long')
    return s


def date_of(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = clean(value)
    if s is None:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue    # expected: try the next date format; error raised below if none match
    raise ValueError(f'date must look like 2028-08-07 or 07/08/2028: {value!r}')


def rx_of(value):
    """True prescription flag -> 1, no -> 0, unknown or unclear -> None (pharmacist must confirm)."""
    s = clean(value)
    if s is None:
        return None
    low = s.lower()
    if low.startswith(('yes', 'y', 'haan', 'true', '1')):
        return 1
    if low.startswith(('no', 'n', 'false', '0')):
        return 0
    return None


def name_key(name):
    return re.sub(r'\s+', ' ', name or '').strip().lower()


# ---------- row checks (pure) ----------

def check_row(raw, today):
    """Check one row (dict with canonical keys). Returns (clean_row, errors, warnings)."""
    errors, warnings = [], []
    row = {}

    name = re.sub(r'\s+', ' ', (clean(raw.get('name')) or '')).strip()
    if not name:
        errors.append('name is required')
    elif len(name) > MAX_NAME:
        errors.append(f'name is longer than {MAX_NAME} characters')
    row['name'] = name

    for key, limit in (('product_code', 30), ('category', 50), ('generic_name', 150), ('manufacturer', 120),
                       ('strength', 60), ('dosage_form', 40), ('supplier', 100)):
        value = clean(raw.get(key))
        if value and len(value) > limit:
            errors.append(f'{key} is longer than {limit} characters')
            value = None
        row[key] = value

    try:
        row['barcode'] = barcode_of(raw.get('barcode'))
        if row['barcode'] and len(row['barcode']) not in (8, 12, 13, 14):
            warnings.append('barcode length is not 8, 12, 13 or 14 digits (not a standard GS1 code)')
    except ValueError as e:
        errors.append(str(e))
        row['barcode'] = None

    for key in ('purchase_price', 'selling_price'):
        try:
            row[key] = money(raw.get(key))
        except ValueError as e:
            errors.append(f'{key}: {e}')
            row[key] = None
    if row['selling_price'] is None and not any(e.startswith('selling_price') for e in errors):
        errors.append('selling price is required')
    if row['purchase_price'] is not None and row['selling_price'] is not None \
            and row['purchase_price'] > row['selling_price']:
        warnings.append('purchase price is higher than selling price (check the cost)')

    for key, label in (('stock_quantity', 'stock quantity'), ('minimum_stock', 'minimum stock')):
        try:
            row[key] = whole_number(raw.get(key), label)
        except ValueError as e:
            errors.append(str(e))
            row[key] = None
    if row['stock_quantity'] is None:
        row['stock_quantity'] = 0
    if row['minimum_stock'] is None:
        row['minimum_stock'] = DEFAULT_REORDER

    batch = clean(raw.get('batch_number'))
    if batch and len(batch) > MAX_BATCH:
        errors.append(f'batch number is longer than {MAX_BATCH} characters')
        batch = None
    row['batch_number'] = batch

    try:
        row['expiry_date'] = date_of(raw.get('expiry_date'))
    except ValueError as e:
        errors.append(str(e))
        row['expiry_date'] = None
    try:
        row['manufacturing_date'] = date_of(raw.get('manufacturing_date'))
    except ValueError as e:
        errors.append(str(e))
        row['manufacturing_date'] = None

    if row['expiry_date']:
        if row['expiry_date'] < today:
            errors.append('expiry date has already passed')
        elif row['expiry_date'] <= today + timedelta(days=EXPIRY_WARN_DAYS):
            warnings.append(f'expires within {EXPIRY_WARN_DAYS} days')
    if row['stock_quantity'] > 0 and not (batch and row['expiry_date']):
        warnings.append('stock has no batch and expiry date: it will be added without expiry tracking')

    row['rx_required'] = rx_of(raw.get('rx_required'))
    row['rx_unknown'] = row['rx_required'] is None
    return row, errors, warnings


# ---------- reading files ----------

def normalise_header(h):
    key = re.sub(r'[^a-z0-9]+', '_', str(h or '').strip().lower()).strip('_')
    return HEADER_ALIASES.get(key, key)


def read_file(path_or_bytes, filename):
    """Return (rows, header_warnings). rows are dicts with canonical keys. Raises ValueError."""
    name = (filename or '').lower()
    if name.endswith('.xlsx'):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, bytes) else path_or_bytes,
                                    data_only=True, read_only=True)
        ws = wb.worksheets[0]
        table = [list(r) for r in ws.iter_rows(values_only=True)]
        if not table:
            raise ValueError('the file is empty')
        headers = [normalise_header(h) for h in table[0]]
        body = [dict(zip(headers, r)) for r in table[1:] if any(c not in (None, '') for c in r)]
    elif name.endswith('.csv'):
        text = path_or_bytes.decode('utf-8-sig') if isinstance(path_or_bytes, bytes) else open(
            path_or_bytes, encoding='utf-8-sig').read()
        reader = csv.reader(io.StringIO(text))
        table = [r for r in reader if any(c.strip() for c in r)]
        if not table:
            raise ValueError('the file is empty')
        headers = [normalise_header(h) for h in table[0]]
        body = [dict(zip(headers, r)) for r in table[1:]]
    else:
        raise ValueError('only .csv and .xlsx files are accepted')

    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ValueError('missing required column(s): ' + ', '.join(missing))
    ignored = sorted(h for h in set(headers) if h and h not in CANON_COLUMNS)
    warnings = [f'ignored column(s): {", ".join(ignored)}'] if ignored else []
    return body, warnings


# ---------- planning ----------

def build_plan(raw_rows, existing, today, update_existing=False):
    """existing = {'barcodes': {barcode: row}, 'names': {name_key: row}} from the database.
    Returns (plan, summary). Each plan item has: line, action, row, errors, warnings, medicine_id."""
    plan, seen_barcode, seen_name = [], {}, {}
    for n, raw in enumerate(raw_rows, start=2):           # line 1 is the header
        row, errors, warnings = check_row(raw, today)
        item = {'line': n, 'name': row['name'], 'barcode': row['barcode'], 'row': row,
                'errors': errors, 'warnings': warnings, 'action': 'error', 'medicine_id': None}
        if not errors:
            key = name_key(row['name'])
            if row['barcode'] and row['barcode'] in seen_barcode:
                errors.append(f"barcode is repeated in this file (line {seen_barcode[row['barcode']]})")
            elif key in seen_name:
                errors.append(f"name is repeated in this file (line {seen_name[key]})")
            else:
                match = (existing['barcodes'].get(row['barcode']) if row['barcode'] else None) \
                    or existing['names'].get(key)
                if row['barcode']:
                    seen_barcode[row['barcode']] = n
                seen_name[key] = n
                if match:
                    item['medicine_id'] = match['medicine_id']
                    item['action'] = 'update' if update_existing else 'skip'
                    warnings.append(f"already in the shop database as #{match['medicine_id']}")
                else:
                    item['action'] = 'create'
        plan.append(item)
    summary = summarise(plan)
    return plan, summary


def summarise(plan):
    counts = {'create': 0, 'update': 0, 'skip': 0, 'error': 0}
    missing = {'strength': 0, 'manufacturer': 0, 'generic_name': 0, 'rx_required': 0, 'barcode': 0}
    for item in plan:
        counts[item['action']] += 1
        r = item['row']
        if item['action'] != 'error':
            for k in missing:
                if r.get(k) in (None, '') or (k == 'rx_required' and r.get('rx_unknown')):
                    missing[k] += 1
    return {'rows': len(plan), 'counts': counts, 'missing_fields': missing,
            'can_commit': counts['error'] == 0 and len(plan) > 0}


# ---------- writing ----------

def apply_plan(cur, plan, source, audit_fn=None):
    """Write the plan with the caller's cursor. The caller commits, or rolls back on any exception.
    Returns counts of what was written."""
    cur.execute("SELECT category_id, category_name FROM categories")
    categories = {r['category_name'].lower(): r['category_id'] for r in cur.fetchall()}
    done = {'created': 0, 'updated': 0, 'batches': 0, 'categories_added': 0}

    def category_id(label):
        if not label:
            return None
        key = label.lower()
        if key not in categories:
            cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (label,))
            categories[key] = cur.lastrowid
            done['categories_added'] += 1
        return categories[key]

    for item in plan:
        row = item['row']
        if item['action'] == 'create':
            cur.execute("""INSERT INTO medicines (name, barcode, category_id, price, cost_price, stock_quantity,
                                                  reorder_level, generic_name, manufacturer, strength, dosage_form,
                                                  rx_required, product_code, import_source)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (row['name'], row['barcode'], category_id(row['category']), row['selling_price'],
                         row['purchase_price'] or Decimal('0.00'), row['stock_quantity'], row['minimum_stock'],
                         row['generic_name'], row['manufacturer'], row['strength'], row['dosage_form'],
                         row['rx_required'], row['product_code'], source))
            mid = cur.lastrowid
            if row['stock_quantity'] > 0 and row['batch_number'] and row['expiry_date']:
                cur.execute("""INSERT INTO batches (medicine_id, batch_number, expiry_date, quantity, purchase_price)
                               VALUES (%s,%s,%s,%s,%s)""",
                            (mid, row['batch_number'], row['expiry_date'], row['stock_quantity'],
                             row['purchase_price']))
                done['batches'] += 1
            done['created'] += 1
            if audit_fn:
                audit_fn(cur, 'medicine.import', 'medicine', mid,
                         f"Imported from {source}: {row['name']}, stock {row['stock_quantity']}",
                         after={'name': row['name'], 'barcode': row['barcode'], 'stock': row['stock_quantity'],
                                'price': str(row['selling_price']), 'rx_required': row['rx_required']})
        elif item['action'] == 'update':
            # Only descriptive fields and prices. Stock and batches are never changed by an import.
            changes = {'price': row['selling_price'], 'cost_price': row['purchase_price'],
                       'reorder_level': row['minimum_stock'], 'generic_name': row['generic_name'],
                       'manufacturer': row['manufacturer'], 'strength': row['strength'],
                       'dosage_form': row['dosage_form'], 'rx_required': row['rx_required'],
                       'product_code': row['product_code'],
                       'category_id': category_id(row['category'])}
            changes = {k: v for k, v in changes.items() if v is not None}
            if not changes:
                continue
            sets = ', '.join(f'{k} = %s' for k in changes)
            cur.execute(f"UPDATE medicines SET {sets}, import_source = %s WHERE medicine_id = %s",
                        list(changes.values()) + [source, item['medicine_id']])
            done['updated'] += 1
            if audit_fn:
                audit_fn(cur, 'medicine.import_update', 'medicine', item['medicine_id'],
                         f"Updated from {source}: {', '.join(changes)}", after={k: str(v) for k, v in changes.items()})
    return done


# ---------- schema (added by core.ensure_schema only when missing; old databases keep working) ----------

PRODUCT_COLUMNS = [
    ('product_code', 'VARCHAR(30) NULL'),
    ('generic_name', 'VARCHAR(150) NULL'),          # salt, used for substitute search (Phase 4)
    ('manufacturer', 'VARCHAR(120) NULL'),
    ('strength', 'VARCHAR(60) NULL'),
    ('dosage_form', 'VARCHAR(40) NULL'),
    ('pack_size', 'VARCHAR(40) NULL'),
    ('rack_location', 'VARCHAR(40) NULL'),
    ('rx_required', 'TINYINT(1) NULL'),             # NULL = unknown, pharmacist must confirm
    ('schedule', 'VARCHAR(20) NULL'),               # controlled-drug schedule (register comes in B8)
    ('tax_rate', 'DECIMAL(5,2) NULL'),              # stored for later per-product tax; sales still use the shop rate
    ('import_source', 'VARCHAR(60) NULL'),
]
