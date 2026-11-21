"""Convert the 230-product Word master list (one 9-row table per product) to a CSV for import.

Run:  python scripts/docx_products_to_csv.py database/samples/MediGen_AI_Pro_230_Pharmacy_Products.docx
      -> writes database/samples/pharmacy_products_230_demo.csv (same folder as the .docx, or give --out)

Placeholders such as "Verify brand / pack" are kept as written: the importer turns them into NULL.
Prices like "PKR 1,240" become 1240.00. The file is DEMO data: barcodes, prices, batches and expiry
dates are examples, not verified stock. Do not sell from it.
"""
import argparse
import csv
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
FIELD_MAP = {
    'Product ID': 'product_code', 'Product Name': 'name', 'Barcode (demo)': 'barcode',
    'Category': 'category', 'Generic Name': 'generic_name', 'Manufacturer': 'manufacturer',
    'Strength': 'strength', 'Dosage Form / Unit': 'dosage_form', 'Purchase Price (demo)': 'purchase_price',
    'Selling Price (demo)': 'selling_price', 'Stock Qty (demo)': 'stock_quantity',
    'Minimum Stock (demo)': 'minimum_stock', 'Batch Number (demo)': 'batch_number',
    'Manufacturing Date (demo)': 'manufacturing_date', 'Expiry Date (demo)': 'expiry_date',
    'Supplier (demo)': 'supplier', 'Prescription Required': 'rx_required',
}
HEADERS = list(FIELD_MAP.values())
SKIP_HEADINGS = ('MediGen AI Pro', 'PHARMACY PRODUCT MASTER', 'Original 230', 'DATA NOTES')


def money_text(v):
    """'PKR 1,240' -> '1240.00'; anything else is kept as written."""
    m = re.fullmatch(r'\s*(?:PKR\s*)?([\d,]+(?:\.\d+)?)\s*', v or '', re.I)
    return f"{float(m.group(1).replace(',', '')):.2f}" if m else (v or '')


def read_products(path):
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    category, out = '', []
    for el in root.find(W + 'body'):
        if el.tag == W + 'p':
            text = ''.join(n.text or '' for n in el.iter(W + 't')).strip()
            if text and not text[:1].isdigit() and len(text) < 60 and not text.startswith(SKIP_HEADINGS):
                category = text
        elif el.tag == W + 'tbl':
            raw = {}
            for r in el.findall(W + 'tr'):
                cells = [''.join(n.text or '' for n in c.iter(W + 't')).strip() for c in r.findall(W + 'tc')]
                for i in range(0, len(cells) - 1, 2):
                    if cells[i] in FIELD_MAP:
                        raw[FIELD_MAP[cells[i]]] = cells[i + 1]
            if raw:
                raw.setdefault('category', category)
                raw['purchase_price'] = money_text(raw.get('purchase_price', ''))
                raw['selling_price'] = money_text(raw.get('selling_price', ''))
                out.append({h: raw.get(h, '') for h in HEADERS})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('docx')
    ap.add_argument('--out', help='CSV path (default: pharmacy_products_230_demo.csv next to the .docx)')
    args = ap.parse_args()
    rows = read_products(args.docx)
    if not rows:
        sys.exit('no product tables found in the file')
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.docx)), 'pharmacy_products_230_demo.csv')
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f'{len(rows)} products written to {out}')


if __name__ == '__main__':
    main()
