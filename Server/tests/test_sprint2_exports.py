"""Sprint 2 checks: Excel and PDF report files, tax summary wiring. No MySQL needed. Run through tests/run_all.py."""
import os as _os, io, sys, importlib.util
from datetime import date, datetime
from decimal import Decimal
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

from pharmacy.exports import build_xlsx, build_pdf, to_cell
from openpyxl import load_workbook

ok(to_cell(Decimal('12.50')) == 12.5 and isinstance(to_cell(Decimal('1')), float), 'decimals become numbers')
ok(to_cell(date(2026, 10, 17)) == '2026-10-17' and to_cell(None) == '', 'dates become text, empty becomes blank')
ok(to_cell(datetime(2026, 10, 17, 9, 5)) == '2026-10-17 09:05', 'date-times are readable')

rows = [(date(2026, 10, 1), 2, Decimal('150.50')), (date(2026, 10, 2), 1, Decimal('20'))]
x = build_xlsx('Sales report', ['Date', 'Invoices', 'Net revenue (Rs.)'], rows,
               summary=[('Net revenue (Rs.)', Decimal('170.50'))], notes=['Check with your accountant'])
ok(x[:2] == b'PK', 'xlsx file is a valid zip container')
wb = load_workbook(io.BytesIO(x))
ws = wb.active
ok(ws['A1'].value == 'Sales report', 'xlsx has the title')
ok([ws.cell(row=3, column=c).value for c in (1, 2, 3)] == ['Date', 'Invoices', 'Net revenue (Rs.)'], 'xlsx has the header row')
ok(ws['C4'].value == 150.5 and ws['B5'].value == 1, 'xlsx keeps numbers as numbers')
ok(any(ws.cell(row=r, column=1).value == 'Summary' for r in range(1, 12)), 'xlsx has a summary block')
ok(any(ws.cell(row=r, column=1).value == 'Check with your accountant' for r in range(1, 14)), 'xlsx has the notes')
empty = load_workbook(io.BytesIO(build_xlsx('Empty', ['A', 'B'], [])))
ok(empty.active['A1'].value == 'Empty', 'an empty xlsx still builds')

p = build_pdf('Sales & tax <test>', ['Date', 'Invoices', 'Revenue'], rows,
              summary=[('Total', Decimal('170.5'))], notes=['note'], subtitle='Period: 2026-10-01 to 2026-10-02')
ok(p[:5] == b'%PDF-' and len(p) > 1000, 'pdf file is a real PDF')
ok(build_pdf('Empty', ['A', 'B', 'C', 'D', 'E', 'F', 'G'], [])[:5] == b'%PDF-', 'an empty PDF builds (landscape for wide tables)')

# ---- wiring ----
rep = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'reports.py'), encoding='utf-8').read()
ok("fmt = request.args.get('fmt', 'csv')" in rep and "'tax'" in rep, 'export accepts csv, xlsx, pdf and the tax summary')
ok("'Sales tax summary'" in rep and 'tax_amount' in rep, 'tax summary reads the tax amount from sales')
ok("@role_required('Admin')" in rep.split('def export_report')[0][-200:], 'exports are for Admin only')
ok('Tax on returned sales is not reversed automatically' in rep, 'tax summary states its limit on returns')
html = open(_os.path.join(ROOT, 'templates', 'reports.html'), encoding='utf-8').read()
ok("rtype='tax'" in html and "fmt='pdf'" in html and "fmt='xlsx'" in html, 'reports page has Excel, PDF and tax buttons')
ok(_os.path.exists(_os.path.join(ROOT, 'pharmacy', 'exports.py')), 'exports module exists')
req = open(_os.path.join(ROOT, 'requirements.txt'), encoding='utf-8').read()
ok('openpyxl' in req and 'reportlab' in req, 'requirements list openpyxl and reportlab')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
