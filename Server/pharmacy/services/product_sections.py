"""v86: product sections. Every product belongs to one section, decided by its dosage form.

Sections: Medicines (tablets, capsules, etc.), Syrups & Suspensions, Creams & Gels, Drip & Injection,
Bandages & Other products. Pure rules here; DB helpers take a cursor and never commit.
"""
import logging
import csv
import io
import re

from pharmacy.services import drip_record as DR

SECTIONS = [
    ('medicines', 'Medicines', 'bi-capsule', 'Tablets, capsules and other medicines'),
    ('syrups', 'Syrups & Suspensions', 'bi-cup-straw', 'Syrups, suspensions, drops and oral liquids'),
    ('creams', 'Creams & Gels', 'bi-droplet', 'Creams, gels, ointments and topical products'),
    ('drip', 'Drip & Injection', 'bi-droplet-half', 'Injections and IV drips (records and expiry)'),
    ('other', 'Bandages & Other', 'bi-bandaid', 'Bandage packs, dressings, syringes and other products'),
]
SECTION_KEYS = [s[0] for s in SECTIONS]
SECTION_LABEL = {s[0]: s[1] for s in SECTIONS}
DEFAULT_FORM = {'medicines': 'Tablet', 'syrups': 'Oral liquid', 'creams': 'Topical cream/gel/ointment',
                'drip': 'Injection', 'other': 'Other product'}
SECTION_CATEGORY = {'medicines': 'Medicines', 'syrups': 'Syrups', 'creams': 'Creams & Gels',
                    'drip': 'Injections', 'other': 'Bandages & Other'}
FORM_CHOICES = {
    'medicines': ['Tablet', 'Capsule', 'Powder', 'Sachet', 'Suppository', 'Inhaler', 'Other'],
    'syrups': ['Oral liquid', 'Syrup', 'Suspension', 'Drops', 'Oral rinse', 'Oral solution'],
    'creams': ['Topical cream/gel/ointment', 'Cream', 'Gel', 'Ointment', 'Lotion'],
    'drip': ['Injection', 'Drip / IV fluid'],
    'other': ['Bandage', 'Dressing', 'Syringe', 'Gauze / cotton', 'Plaster', 'Other product'],
}
ALL_FORM_CHOICES = list(dict.fromkeys(f for fl in FORM_CHOICES.values() for f in fl))   # v86.41: bulk edit
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 3000
PLACEHOLDER = re.compile(r'verify|not provided|product[- ]specific|standard formulation|^n/?a$|^-$|^$', re.IGNORECASE)


def section_for(dosage_form):
    f = (dosage_form or '').strip().lower()
    if DR.is_drip_form(f):
        return 'drip'
    if re.search(r'syrup|suspension|oral liquid|drop|oral solution|elixir|linctus|emulsion|rinse|mixture', f):
        return 'syrups'
    if re.search(r'cream|gel|ointment|lotion|topical|paste|balm|spray', f):
        return 'creams'
    if re.search(r'bandage|dressing|gauze|cotton|plaster|syringe|cannula|swab|glove|mask|strip|surgical|tape|kit|other product', f):
        return 'other'
    return 'medicines'


def clean_form(text):
    """'Oral liquid (formulation varies)' -> 'Oral liquid'. Empty or placeholder -> None."""
    t = re.sub(r'\(.*?\)', '', text or '').strip()
    if not t or PLACEHOLDER.search(t):
        return None
    return t[:50]


def clean_text(text, limit=100):
    t = (text or '').strip()
    if not t or PLACEHOLDER.search(t):
        return None
    return t[:limit]


def _header(h):
    return (h or '').strip().lower().replace(' ', '_')


def _pick(row, *keys):
    for k in keys:
        v = (row.get(k) or '').strip()
        if v:
            return v
    return ''


NAME_KEYS = ('generic_name', 'generic_ingredient', 'generic', 'name', 'product_name', 'product', 'medicine',
             'medicine_name', 'item', 'item_name', 'title', 'drug', 'drug_name', 'description')
FORM_KEYS = ('dosage_form', 'form', 'type')
JUNK_STRENGTH = {'0', '0.0', '0.00', 'nil', 'none', 'null', 'na', 'n/a', '-'}
UNIT_RE = re.compile(r'\b(mg|mcg|g|ml|l|iu|%|mg/ml|mg/5 ?ml)\b', re.IGNORECASE)


def _clean_name(text):
    """Removes list numbers, bullets and 'Rs 120' price tails from a name."""
    t = re.sub(r'^\s*(\d{1,3}[.)]|[-*\u2022])\s+', '', text or '').strip()
    t = re.sub(r'\s*(\||\t)?\s*Rs\.?\s*\d[\d.,]*\s*$', '', t, flags=re.IGNORECASE).strip()
    return t


def parse_products_report(raw_bytes, section):
    """Reads a CSV for one section. Returns (items, errors, warnings).
    errors  = the file cannot be used at all (shown as one clear message).
    warnings = a row was skipped or fixed; the good rows are still imported.
    Column names may vary; ; and tab separators work; a file with no name header uses its first column."""
    if section not in SECTION_KEYS:
        return [], ['Unknown section.'], []
    if len(raw_bytes) > MAX_BYTES:
        return [], ['The file is larger than 2 MB. Split it into smaller files.'], []
    text = None
    for enc in ('utf-8-sig', 'cp1252'):
        try:
            text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return [], ['The file could not be read. Save it again as "CSV UTF-8" from Excel.'], []
    first = text.strip().splitlines()[0] if text.strip() else ''
    delim = ','
    if first.count(';') > first.count(',') and first.count(';') > 0:
        delim = ';'
    elif first.count('\t') > first.count(',') and first.count('\t') > 0:
        delim = '\t'
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = [_header(h) for h in (reader.fieldnames or [])]
    reader.fieldnames = headers
    rows = [{k: str(v or '') for k, v in r.items() if k} for r in reader]
    warnings = []
    name_key = next((k for k in NAME_KEYS if k in headers), None)
    if name_key is None:
        if not headers or not any(r.get(headers[0], '').strip() for r in rows):
            return [], ["The file needs a name column. Write 'name' or 'generic_name' in the first line, then upload again."], []
        name_key = headers[0]
        warnings.append(f"No name column found, so the first column '{headers[0]}' is used as the name.")
    items, seen = [], set()
    for line_no, row in enumerate(rows, start=2):
        if not any(v.strip() for v in row.values()):
            continue
        if len(items) >= MAX_ROWS:
            return [], [f'The file has more than {MAX_ROWS} items. Split it into two files.'], warnings
        generic = clean_text(_clean_name(_pick(row, name_key, *NAME_KEYS)), 100)
        if not generic:
            warnings.append(f'Line {line_no}: name is empty, skipped.')
            continue
        form = clean_form(_pick(row, *FORM_KEYS))
        if section == 'drip':
            raw_form = _pick(row, *FORM_KEYS).lower()
            if not raw_form or section_for(raw_form) != 'drip':
                warnings.append(f"Line {line_no} ({generic}): '{raw_form or 'no form'}' is not an injection or drip, skipped.")
                continue
            form = 'Drip / IV fluid' if ('infusion' in raw_form or 'iv solution' in raw_form or 'drip' in raw_form) else 'Injection'
        elif not form or section_for(form) != section:
            form = DEFAULT_FORM[section]           # file form does not fit this section: use the section default
        strength = clean_text(_pick(row, 'strength', 'common_strength_or_concentration'), 60)
        if strength and strength.lower() in JUNK_STRENGTH:
            strength = None                        # '0', 'nil' and similar are not a strength
        brand = clean_text(_pick(row, 'brand_name', 'brand'), 60)
        name = generic
        if strength and strength.lower() not in generic.lower():
            name = f'{generic} {strength}'
        if brand and brand.lower() not in name.lower():
            name = f'{name} ({brand})'
        name = name[:100]
        if name.lower() in seen:
            continue                               # same name again: already in this list
        seen.add(name.lower())
        barcode = re.sub(r'\D', '', _pick(row, 'barcode'))[:64] or None
        rx = _pick(row, 'prescription_required', 'rx', 'rx_required').lower()
        def _money(raw):
            raw = (raw or '').replace(',', '').strip()
            mm = re.search(r'\d+(\.\d+)?', raw)
            return float(mm.group(0)) if mm else 0.0
        price = _money(_pick(row, 'price', 'rate', 'rates', 'sale_price', 'selling_price', 'retail_price', 'mrp', 'unit_price'))
        cost = _money(_pick(row, 'cost_price', 'cost', 'purchase_price', 'trade_price', 'tp'))
        qty_raw = _pick(row, 'quantity', 'stock', 'stock_quantity', 'qty').strip()
        qty = 0
        if qty_raw:
            m = re.search(r'\d+(\.\d+)?', qty_raw)          # '10', '10 pcs', '10.0' all read as 10
            if m:
                qty = int(float(m.group(0)))
            else:
                warnings.append(f'Line {line_no} ({generic}): quantity "{qty_raw}" is not a number, stock set to 0.')
        items.append({
            'qty': max(qty, 0),
            'name': name, 'generic_name': generic, 'strength': strength, 'dosage_form': form,
            'barcode': barcode, 'price': price, 'cost_price': cost,
            'rx_required': 1 if rx in ('yes', '1', 'true') else 0,
            'product_code': _pick(row, 'product_id', 'product_code')[:50] or None,
        })
    if not items:
        return [], ['No item was found. Check that the file has medicine names, and that the first line is a header (name or generic_name).'], warnings
    return items, [], warnings


def parse_products(raw_bytes, section):
    """Same as parse_products_report without the warnings. Returns (items, errors)."""
    items, errors, _ = parse_products_report(raw_bytes, section)
    return items, errors


DATE_RE = re.compile(r'\b\d{1,2}[ /.-](jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b', re.IGNORECASE)


def _is_header_or_date(name):
    """Table headers, titles, dates, page numbers and totals are not medicine names."""
    if DATE_RE.search(name) or re.match(r'(page|total)\b', name, re.IGNORECASE):
        return True
    return len(PHOTO_SKIP_WORDS.findall(name)) >= 2


PHOTO_SKIP_WORDS = re.compile(r'\b(sr|s\.?no|no|name|price|qty|quantity|stock|total|date|sale|rs|amount|invoice|bill|page|batch|expiry)\b', re.IGNORECASE)


def photo_lines_to_csv(lines):
    """Turns OCR lines from a photo of a list into CSV bytes with one 'name' column.
    Lines with too few letters or table headers are dropped."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['name'])
    kept = 0
    for ln in lines:
        name = _clean_name(ln)
        letters = sum(ch.isalpha() for ch in name)
        if letters < 3 or _is_header_or_date(name) or (PHOTO_SKIP_WORDS.search(name) and letters < 12):
            continue
        w.writerow([name[:100]])
        kept += 1
    return out.getvalue().encode('utf-8'), kept


def import_items(cur, items, section, user_id, source):
    """Writes the new items for one section. Existing names and barcodes are skipped. Returns (added, skipped)."""
    added = skipped = 0
    cat_name = SECTION_CATEGORY[section]
    cur.execute("SELECT category_id FROM categories WHERE category_name=%s", (cat_name,))
    row = cur.fetchone()
    if row:
        cid = row['category_id']
    else:
        cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (cat_name,))
        cid = cur.lastrowid
    for it in items:
        cur.execute("SELECT medicine_id FROM medicines WHERE name=%s", (it['name'],))
        if cur.fetchone():
            skipped += 1
            continue
        barcode = it['barcode']
        if barcode:
            cur.execute("SELECT medicine_id FROM medicines WHERE barcode=%s", (barcode,))
            if cur.fetchone():
                barcode = None
        cur.execute("""INSERT INTO medicines (name, barcode, category_id, price, cost_price, stock_quantity, reorder_level,
                                             generic_name, strength, dosage_form, rx_required, product_code, import_source)
                       VALUES (%s,%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s)""",
                    (it['name'], barcode, cid, float(it.get('price') or 0), float(it.get('cost_price') or 0),
                     it.get('qty', 0), it['generic_name'], it['strength'], it['dosage_form'],
                     it['rx_required'], it['product_code'], source[:100]))
        qty = int(it.get('qty') or 0)
        if qty > 0:
            from pharmacy.repos import medicines as _repo
            _repo.insert_opening_stock(cur, cur.lastrowid, user_id, qty)
        added += 1
    return added, skipped


def overview(cur):
    """Per section: items, in stock, low stock, out of stock, batches expiring in 90 days, units sold today."""
    out = {k: {'items': 0, 'in_stock': 0, 'low': 0, 'out': 0, 'expiring': 0, 'sold_today': 0, 'sold_week': 0} for k in SECTION_KEYS}
    cur.execute("SELECT medicine_id, dosage_form, stock_quantity, reorder_level FROM medicines WHERE is_deleted = 0")
    sec_of = {}
    for r in cur.fetchall():
        s = section_for(r['dosage_form'])
        sec_of[r['medicine_id']] = s
        o = out[s]
        o['items'] += 1
        qty = int(r['stock_quantity'] or 0)
        if qty > 0:
            o['in_stock'] += 1
            if qty <= int(r['reorder_level'] or 0):
                o['low'] += 1
        else:
            o['out'] += 1
    cur.execute("""SELECT medicine_id, COUNT(*) AS n FROM batches
                   WHERE quantity > 0 AND expiry_date BETWEEN CURDATE() AND CURDATE() + INTERVAL 90 DAY
                   GROUP BY medicine_id""")
    for r in cur.fetchall():
        if r['medicine_id'] in sec_of:
            out[sec_of[r['medicine_id']]]['expiring'] += int(r['n'])
    cur.execute("""SELECT si.medicine_id, SUM(si.quantity) AS q FROM sale_items si
                   JOIN sales s ON s.sale_id = si.sale_id
                   WHERE DATE(s.sale_date) = CURDATE() GROUP BY si.medicine_id""")
    for r in cur.fetchall():
        if r['medicine_id'] in sec_of:
            out[sec_of[r['medicine_id']]]['sold_today'] += int(r['q'] or 0)
    cur.execute("""SELECT si.medicine_id, SUM(si.quantity) AS q FROM sale_items si
                   JOIN sales s ON s.sale_id = si.sale_id
                   WHERE s.sale_date >= CURDATE() - INTERVAL 6 DAY GROUP BY si.medicine_id""")
    for r in cur.fetchall():
        if r['medicine_id'] in sec_of:
            out[sec_of[r['medicine_id']]]['sold_week'] += int(r['q'] or 0)
    top = max([v['sold_week'] for v in out.values()] + [1])
    for v in out.values():
        v['week_pct'] = round(100 * v['sold_week'] / top)
    return out


def _ocr_pdf(raw_bytes):
    """Returns (lines, errors). Uses the same Tesseract as the prescription photo reader."""
    import os, subprocess, tempfile
    from pharmacy.services import rx_scan
    exe = rx_scan._tesseract_exe()
    if not exe:
        return [], ['This PDF has no text (scanned). OCR is not installed on this PC: install Tesseract or use a CSV.']
    try:
        import pdfplumber
        lines = []
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            if len(pdf.pages) > 20:
                return [], ['A scanned PDF can have at most 20 pages. Split it.']
            for page in pdf.pages:
                img = page.to_image(resolution=200).original
                fd, path = tempfile.mkstemp(suffix='.png')
                os.close(fd)
                try:
                    img.save(path)
                    out = subprocess.run([exe, path, 'stdout'], capture_output=True, text=True, timeout=60)
                finally:
                    os.unlink(path)
                lines.extend(ln.strip() for ln in out.stdout.splitlines() if ln.strip())
    except Exception:
        return [], ['The scanned PDF could not be read by OCR. Try a CSV instead.']
    if not lines:
        return [], ['OCR found no text in this PDF.']
    return lines, []


PDF_TEXT_TABLE = {"vertical_strategy": "text", "horizontal_strategy": "text", "min_words_vertical": 2}
STD_COLS = ['name', 'dosage_form', 'strength', 'quantity', 'barcode', 'brand_name', 'price', 'cost_price']  # v93: rates bhi
NAME_WORDS = {'name', 'medicine', 'item', 'product', 'description', 'generic_name', 'generic'}


def _first(d, keys):
    return next((d[k].strip() for k in keys if (d.get(k) or '').strip()), '')


def _table_records(rows, allow_no_header):
    """Turns one table into records. A header row must name a column such as name, medicine or item.
    allow_no_header: a bordered table with no header row uses its first column as the name."""
    hdr = None
    for i, r in enumerate(rows[:3]):
        hs = [_header(c) for c in r]
        if any(h in NAME_KEYS for h in hs):
            hdr = (i + 1, hs)
            break
    if hdr is None and not allow_no_header:
        return []
    start, hs = hdr if hdr else (0, None)
    out = []
    for r in rows[start:]:
        if hs is None:
            rec = {'name': r[0] if r else ''}
        else:
            d = {hs[j]: (r[j] if j < len(r) else '') for j in range(len(hs)) if hs[j]}
            rec = {'name': _first(d, NAME_KEYS), 'dosage_form': _first(d, FORM_KEYS),
                   'strength': _first(d, ('strength', 'common_strength_or_concentration')),
                   'quantity': _first(d, ('quantity', 'stock', 'stock_quantity', 'qty')),
                   'barcode': _first(d, ('barcode',)), 'brand_name': _first(d, ('brand_name', 'brand')),
                   'price': _first(d, ('price', 'rate', 'rates', 'sale_price', 'selling_price', 'retail_price', 'mrp', 'unit_price')),
                   'cost_price': _first(d, ('cost_price', 'cost', 'purchase_price', 'trade_price', 'tp'))}
        name = _clean_name(rec.get('name') or '')
        if not name or name.lower() in NAME_WORDS:
            continue
        rec['name'] = name
        out.append(rec)
    return out


def _line_record(line):
    """One line of plain PDF text -> a record with a name, or None for headers, totals, page numbers and numbers."""
    name = _clean_name(re.split(r'\s{2,}|\t', line.strip())[0].strip())
    letters = sum(ch.isalpha() for ch in name)
    if letters < 3 or sum(ch.isdigit() for ch in name) > letters:
        return None
    if _is_header_or_date(name):
        return None
    return {'name': name}


def _ocr_page(page, exe):
    """OCR of one page picture (for a scanned page that has no text layer)."""
    import os, subprocess, tempfile
    img = page.to_image(resolution=200).original
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    try:
        img.save(path)
        out = subprocess.run([exe, path, 'stdout'], capture_output=True, text=True, timeout=60)
        return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    finally:
        os.unlink(path)


def pdf_to_csv_bytes(raw_bytes):
    """v86.44: any PDF list. Reads bordered tables, borderless tables, plain text lines, and scanned pages (OCR).
    Each page is read on its own, so one scanned page does not block the others.
    Returns (csv_bytes, errors)."""
    from pharmacy.services import rx_scan
    try:
        import pdfplumber
    except ImportError:
        return None, ['PDF reading is not installed on this computer (pdfplumber).']
    try:
        pdf = pdfplumber.open(io.BytesIO(raw_bytes))
    except Exception:
        return None, ['The PDF could not be opened. If it has a password, remove it and try again.']
    exe = rx_scan._tesseract_exe()
    records, scanned_without_ocr = [], 0
    try:
        with pdf:
            if len(pdf.pages) > 60:
                return None, ['The PDF has more than 60 pages. Split it into parts.']
            for page in pdf.pages:
                tables = []
                for t in page.extract_tables() or []:
                    if t and len(t) >= 2:
                        tables.append((t, True))
                if not tables:
                    try:
                        for t in page.extract_tables(PDF_TEXT_TABLE) or []:
                            if t and len(t) >= 3:
                                tables.append((t, False))
                    except Exception as exc:
                        logging.getLogger('medigen.products').warning('PDF text-table fallback failed (%s)', type(exc).__name__)
                clean = lambda t: [[(c or '').replace('\n', ' ').strip() for c in r] for r in t
                                   if any((c or '').strip() for c in r)]
                got = []
                for t, bordered in tables:
                    got.extend(_table_records(clean(t), bordered))
                if got:
                    records.extend(got)
                    continue
                text = page.extract_text() or ''
                if text.strip():
                    for line in text.splitlines():
                        rec = _line_record(line)
                        if rec:
                            records.append(rec)
                elif exe:
                    for line in _ocr_page(page, exe):
                        rec = _line_record(line)
                        if rec:
                            records.append(rec)
                else:
                    scanned_without_ocr += 1
    except Exception:
        return None, ['The PDF could not be read. Try a CSV instead.']
    if not records:
        if scanned_without_ocr:
            return None, ['This PDF is a scanned picture. Install the free OCR program (Tesseract, see TESSERACT_INSTALL_ROMAN_URDU.md) or use a CSV.']
        return None, ['No medicine names were found in this PDF. Check that it has a list of names.']
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(STD_COLS)
    seen = set()
    for rec in records:
        key = rec['name'].lower()
        if key in seen:
            continue
        seen.add(key)
        writer.writerow([rec.get(c, '') or '' for c in STD_COLS])
    return buf.getvalue().encode('utf-8'), []


