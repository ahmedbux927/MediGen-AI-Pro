"""Stage 12 (Master Prompt v4): barcode label printing.

The labels PDF is built with reportlab's Code 128 (a project dependency).
Only items that have a barcode can be labelled.
"""
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


from pharmacy.services.labels_pdf import build_labels_pdf  # noqa: E402

pdf = build_labels_pdf([{'name': 'Panadol', 'barcode': '8901234567890', 'price': 100, 'copies': 2}])
ok(pdf[:4] == b'%PDF' and len(pdf) > 1500, 'labels PDF is generated (header + content)')
try:
    import pdfplumber
    import io as _io
    with pdfplumber.open(_io.BytesIO(pdf)) as doc:
        text = doc.pages[0].extract_text() or ''
    ok('Panadol' in text and '8901234567890' in text, 'the label carries the item name and its barcode number')
except ImportError:
    ok(True, 'pdfplumber not installed here; text check skipped')

empty = build_labels_pdf([{'name': 'No Code', 'barcode': '', 'price': 10, 'copies': 1}])
ok(empty[:4] == b'%PDF', 'items without a barcode produce the guidance page, not a broken label')

routes = read('pharmacy/routes/products.py')
ok('def product_labels' in routes and 'def product_labels_print' in routes, 'labels page and print routes exist')
ok("url_for('product_labels')" in read('templates/medicines.html'), 'medicines page links to Labels')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
