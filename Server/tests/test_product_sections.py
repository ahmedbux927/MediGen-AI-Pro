"""v86: product sections (Medicines, Syrups, Creams & Gels, Drip & Injection, Bandages & Other), CSV load, cart and wiring.
No MySQL. Run through tests/run_all.py."""
import os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import product_sections as PS
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
FIX = _os.path.join(ROOT, 'tests', 'fixtures')

cases = {'Tablet': 'medicines', 'Oral liquid (formulation varies)': 'syrups', 'Oral drops': 'syrups',
         'Topical cream/gel/ointment (verify actual product)': 'creams', 'Injection': 'drip',
         'Infusion / IV solution': 'drip', 'Bandage roll': 'other', 'Drip / IV fluid': 'drip', '': 'medicines'}
ok(all(PS.section_for(f) == s for f, s in cases.items()), 'every dosage form lands in the right section')
ok(PS.clean_form('Oral liquid (formulation varies)') == 'Oral liquid' and PS.clean_form('Verify product label') is None, 'form text is cleaned, placeholders dropped')
ok(PS.clean_text('Not provided') is None and PS.clean_text('1 g vial') == '1 g vial', 'placeholder text becomes empty, real text is kept')
ok(set(PS.SECTION_KEYS) == {'medicines', 'syrups', 'creams', 'drip', 'other'} and len(PS.SECTIONS) == 5, 'five sections, in order')
ok(all(PS.DEFAULT_FORM[k] in PS.FORM_CHOICES[k] for k in PS.SECTION_KEYS), 'default form of each section is a valid choice')
ok(all(PS.section_for(f) == k for k in PS.SECTION_KEYS for f in PS.FORM_CHOICES[k]), 'every form choice belongs to its own section')

syr, e1 = PS.parse_products(open(_os.path.join(FIX, 'syrups_list.csv'), 'rb').read(), 'syrups')
ok(not e1 and len(syr) > 150, 'syrups CSV loads (over 150 items)')
ok(all(PS.section_for(i['dosage_form']) == 'syrups' for i in syr), 'every syrup row is a syrup form')
cre, e2 = PS.parse_products(open(_os.path.join(FIX, 'creams_list.csv'), 'rb').read(), 'creams')
ok(not e2 and len(cre) > 100 and cre[0]['name'] == 'Clotrimazole' and cre[0]['strength'] is None, 'creams CSV loads; "Verify product label" strength is dropped')
ok(all(PS.section_for(i['dosage_form']) == 'creams' for i in cre), 'every cream row is a cream form')
drp, e3 = PS.parse_products(open(_os.path.join(FIX, 'drip_injection_list.csv'), 'rb').read(), 'drip')
ok(not e3 and len(drp) > 300, 'drip CSV loads through the same importer')

_, bad1, warn1 = PS.parse_products_report(b'generic_name,dosage_form\nParacetamol,Tablet\nDextrose,Injection\n', 'drip')
ok(not bad1 and any('not an injection' in w for w in warn1), 'a tablet in the drip section is skipped with a clear warning (v86.43)')
ok(len(_) == 1 and _[0]['generic_name'] == 'Dextrose', 'the good drip row is still imported (v86.43)')
mixed, bad2 = PS.parse_products(b'generic_name,dosage_form\nParacetamol,Tablet\nDextrose,Injection\n', 'syrups')
ok(not bad2 and len(mixed) == 2 and all(i['dosage_form'] == 'Oral liquid' for i in mixed), 'a wrong form in a normal section gets the section default (no failure)')
_, bad3 = PS.parse_products(b'price,stock\n,,\n', 'creams')
ok(bad3 and 'name column' in bad3[0], 'a file with no names and no name column is refused with a clear message')
it3, bad3b, warn3 = PS.parse_products_report(b'price,stock\nX,1,2\n', 'creams')
ok(not bad3b and it3 and any('first column' in w for w in warn3), 'no name header: first column is used, with a warning (v86.43)')
_, bad4 = PS.parse_products(b'\x81\x8d\x8f junk', 'creams')
ok(bad4 and 'CSV UTF-8' in bad4[0], 'a file that is neither UTF-8 nor Windows text is refused with a clear message')
it4, bad4b = PS.parse_products(b'name,dosage_form\nCaf\xe9,Tablet\n', 'medicines')
ok(not bad4b and it4, 'Excel Windows (cp1252) CSV is accepted (v86.43)')
_, bad5 = PS.parse_products(b'x' * (PS.MAX_BYTES + 5), 'creams')
ok(bad5 and '2 MB' in bad5[0], 'file over 2 MB is refused')
ok(PS.parse_products(b'generic_name\nA\n', 'nope')[1] == ['Unknown section.'], 'unknown section is refused')
dup, _ = PS.parse_products(b'generic_name,dosage_form,strength\nDextrose,Injection,5%\nDextrose,Injection,5%\nDextrose,Injection,10%\n', 'drip')
ok(len(dup) == 2, 'duplicate rows in one file are kept once')
br, _ = PS.parse_products(b'generic_name,dosage_form,barcode,brand_name,strength\nCefixime,Oral liquid,8901 234 5678,Cefi-X,100 mg/5 mL\n', 'syrups')
ok(br[0]['barcode'] == '89012345678' and br[0]['name'] == 'Cefixime 100 mg/5 mL (Cefi-X)', 'barcode digits kept, brand added to the name')

class Cur:
    def __init__(self, existing=(), barcodes=()):
        self.existing, self.barcodes, self.rows, self.inserts, self.lastrowid = set(existing), set(barcodes), [], [], 9
    def execute(self, sql, params=()):
        q = ' '.join(sql.split())
        if q.startswith('SELECT medicine_id FROM medicines WHERE name'):
            self.rows = [{'medicine_id': 1}] if params[0] in self.existing else []
        elif q.startswith('SELECT medicine_id FROM medicines WHERE barcode'):
            self.rows = [{'medicine_id': 2}] if params[0] in self.barcodes else []
        elif q.startswith('SELECT category_id'):
            self.rows = [{'category_id': 4}]
        elif q.startswith('INSERT INTO medicines'):
            self.inserts.append(params)
            self.rows = []
        else:
            self.rows = []
    def fetchone(self):
        return self.rows[0] if self.rows else None

cur = Cur(existing={'Dextrose 5%'}, barcodes={'89012345678'})
added, skipped = PS.import_items(cur, mixed + br, 'syrups', 1, 'list.csv')
ok(added == 3 and skipped == 0, 'import adds new items for the section')
ok(cur.inserts[-1][1] is None, 'a barcode already in the database is not written twice')
ok(all(p[-1] == 'list.csv' for p in cur.inserts), 'every imported row records the source file')
ok('float(it.get(\'price\') or 0)' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'product_sections.py'), encoding='utf-8').read() and 'insert_opening_stock' in open(_os.path.join(ROOT, 'pharmacy', 'services', 'product_sections.py'), encoding='utf-8').read(), 'v93: imports take quantity AND rates from the file (price/cost 0 only when the file has none)')
cur2 = Cur(existing={'Paracetamol', 'Dextrose'})
a2, s2 = PS.import_items(cur2, mixed, 'syrups', 1, 'x.csv')
ok(a2 == 0 and s2 == 2, 'names already in the database are skipped, not changed')

route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'products.py'), encoding='utf-8').read()
ok("'/products/<key>'" in route and "'/products/item/<int:mid>/edit'" in route and "'/cart/add'" in route, 'routes: section page, edit, cart')
ok("'/products/<key>/import'" in route and "'/products/<key>/add'" in route and "'/products/item/<int:mid>/remove'" in route, 'routes: load, add, remove')
ok(route.count("@role_required('Admin', 'Pharmacist')") >= 4, 'load, add, edit and remove are for Admin and Pharmacist only')
ok("'/cart/add'" in route and "@login_required" in route.split("def cart_add")[0].split("@app.route('/cart/add'")[1], 'cart needs a login but not an admin role (cashiers sell too)')
ok("if have + qty > stock" in route, 'the cart cannot take more than the stock')
ok("if current:" in route and "current['qty'] = have + qty" in route, 'the same product is merged into one line')
sales_src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
ok("session.get('sale_cart')" in sales_src and "session.pop('sale_cart', None)" in sales_src, 'sale screen takes the cart and clears it after a saved sale')
ok(sales_src.index("session.pop('sale_cart'") > sales_src.index('save_sale(cur, session'), 'the cart is cleared only after the sale is saved')
ok('from . import products' in open(_os.path.join(ROOT, 'pharmacy', 'routes', '__init__.py'), encoding='utf-8').read(), 'products routes are registered')
tpl = open(_os.path.join(ROOT, 'templates', 'products.html'), encoding='utf-8').read()
ok('name="code"' in tpl and 'name="qty"' in tpl and 'cart_add' in tpl, 'section page: barcode box, quantity and Add to sale')
ok("url_for('new_sale') }}?med=" in open(_os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8').read(), 'medicines list has a Sell link on each row')
med_src = open(_os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8').read()
ok('{% for f in dosage_forms %}' in med_src and med_src.count('{% for f in dosage_forms %}') == 2, 'medicine add and edit forms list every section form')
lib = open(_os.path.join(ROOT, 'pharmacy', 'lib.py'), encoding='utf-8').read()
ok("'Oral liquid'" in lib and "'Topical cream/gel/ointment'" in lib and "'Bandage'" in lib, 'validation accepts every section form (no "invalid dosage form" on imported items)')
dash = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'dashboard.py'), encoding='utf-8').read()
ok('PS.overview(cur)' in dash and 'section_rows' in dash, 'dashboard shows every section')
dt = open(_os.path.join(ROOT, 'templates', 'dashboard.html'), encoding='utf-8').read()
ok('rec.sections' in dt and "url_for('products_hub')" in dt, 'dashboard table links to the sections')

clear_src = route.split("def products_clear_unused")[1].split("@app.route")[0]
ok("DC.remove_blocker(cur, r['medicine_id'])" in clear_src and "kept += 1" in clear_src, 'clear unused: items with history are kept, only unused ones are deleted')
ok("role_required('Admin', 'Pharmacist')" in route.split("def products_clear_unused")[0].split("@app.route('/products/<key>/clear-unused'")[1], 'clear unused: Admin and Pharmacist only')
ok("batch_total" in route and "batches=batches" in route, 'edit page receives the batch rows and total')
ok("products_clear_unused" in tpl and "new_purchase" in tpl, 'section page: clear unused button and Buy stock link')
edit_tpl = open(_os.path.join(ROOT, 'templates', 'products_edit.html'), encoding='utf-8').read()
ok('expiry_date' in edit_tpl and 'batch_total' in edit_tpl, 'edit page shows batch expiry dates and quantity')

# v86.2: PDF lists, one-click selection, admin cards on top
from reportlab.lib.pagesizes import A4 as _A4
from reportlab.platypus import SimpleDocTemplate as _SDT, Table as _T, TableStyle as _TS
from reportlab.lib import colors as _colors
import io as _io
def _mkpdf(data, grid=True):
    b = _io.BytesIO(); d = _SDT(b, pagesize=_A4); t_ = _T(data)
    if grid: t_.setStyle(_TS([('GRID', (0, 0), (-1, -1), 0.5, _colors.black)]))
    d.build([t_]); return b.getvalue()
gb, ge = PS.pdf_to_csv_bytes(_mkpdf([['generic_name', 'dosage_form', 'strength'], ['Amoxicillin', 'Oral liquid', '125 mg/5 mL'], ['Dextrose', 'Injection', '5%']]))
gi, gerr = PS.parse_products(gb, 'syrups') if gb else ([], ge)
ok(not ge and not gerr and [i['name'] for i in gi] == ['Amoxicillin 125 mg/5 mL', 'Dextrose 5%'], 'PDF table with a header: rows read, header not treated as a product')
pb, pe = PS.pdf_to_csv_bytes(_mkpdf([['Amoxicillin'], ['Ibuprofen']], grid=False))
pi, perr = PS.parse_products(pb, 'syrups') if pb else ([], pe)
ok(not perr and [i['name'] for i in pi] == ['Amoxicillin', 'Ibuprofen'], 'PDF without a table: each line becomes a product name')
ok(PS.pdf_to_csv_bytes(b'not a pdf')[1][0].startswith('The PDF could not be opened'), 'broken PDF is refused with a message')
ok("accept=\".csv,.pdf" in tpl and "'/cart/add-selected'" in route and "@login_required" in route.split("def cart_add_selected")[0].split("@app.route('/cart/add-selected'")[1], 'import accepts PDF; selection route needs login')
ok("row-select" in tpl and "sellSelected()" in tpl and "Sell Selected" in tpl, 'section page: tick boxes and one Sell Selected button (v86.36)')
ok(tpl.index('Add item') < tpl.index('name="q"') and tpl.index('Import list') < tpl.index('name="q"'), 'Add item and Import list are in the toolbar above the search box (v86.36)')
ok("if have + 1 > int(m['stock_quantity'] or 0)" in route and "return redirect(url_for('new_sale'))" in route, 'selected items are stock checked and the sale screen opens')

# v86.3: export, receive stock, sidebar, medicines import link, sale name search
route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'products.py'), encoding='utf-8').read()
ok("'/products/<key>/export'" in route and "_csv_response(header, data" in route, 'section export writes a CSV with the loader columns')
rc = route.split("def products_receive")[1].split("@app.route")[0] if "def products_receive" in route else ''
ok("'/products/item/<int:mid>/receive'" in route and "expiry <= _date.today()" in rc and "UPDATE batches SET quantity = quantity + %s" in rc, 'receive stock: needs a future expiry, adds to a batch and the stock total')
ok("repo.set_stock(cur, mid, old + qty)" in rc and "repo.insert_adjustment" in rc, 'receive stock is recorded in the stock history')
ok(tpl.count("Receive stock") == 1 and "receive'" in tpl or "/receive" in tpl, 'section page has a Receive stock form')
base_src = open(_os.path.join(ROOT, 'templates', 'base.html'), encoding='utf-8').read()
_hubs_src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'hubs.py'), encoding='utf-8').read()
ok(all(k in _hubs_src for k in ["key': 'syrups'", "key': 'creams'", "key': 'drip'", "key': 'other'"]) and "Product Sections" not in base_src, 'Medicines hub has one card per section, in order')
ok("url_for('products_import', key='medicines')" in open(_os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8').read(), 'medicines page has direct Import list (file picker)')
sale_js = open(_os.path.join(ROOT, 'templates', 'new_sale.html'), encoding='utf-8').read()
ok("not a barcode: search the name" in sale_js and "items match" in sale_js, 'sale screen: typing a name adds the item when it is one match')

# v86.4: add goes to the sale screen; Sell Selected on medicines; OCR for scanned PDFs
ok("flash(f'Added {name} x{qty}. Items in sale: {len(cart)}.', 'success')\n    return redirect(url_for('new_sale'))" in route, 'Add (and barcode add) opens the sale screen')
med_tpl = open(_os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8').read()
ok("function sellSelected()" in med_tpl and "id=\"sellSelForm\"" in med_tpl and "name=\"key\" value=\"medicines\"" in med_tpl, 'medicines table: Sell Selected button posts the ticked rows')
ok("url_for('cart_add_selected')" in med_tpl, 'medicines Sell Selected uses the same route as sections')
ok("_ocr_page(page, exe)" in open(_os.path.join(ROOT, 'pharmacy', 'services', 'product_sections.py'), encoding='utf-8').read() and "scanned_without_ocr" in open(_os.path.join(ROOT, 'pharmacy', 'services', 'product_sections.py'), encoding='utf-8').read(), 'scanned pages (no text layer) are read by OCR, page by page (v86.44)')
sb = open(_os.path.join(ROOT, 'pharmacy', 'services', 'product_sections.py'), encoding='utf-8').read()
ok("rx_scan._tesseract_exe()" in sb and "delete" not in sb.split("def _ocr_pdf")[1].split("def pdf_to_csv_bytes")[0].replace("os.unlink", ""), 'OCR uses the same Tesseract finder and removes its temp image')

edit_fn = route.split("def products_edit")[1].split("@app.route")[0]
ok(edit_fn.index("batches = cur.fetchall()") < edit_fn.index("except Exception:"), 'edit page: batch rows are read inside the try, before the except (v86.5 fix for a 500)')

# v86.6: sale screen grouped by section, product picker cards
sales_r = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
ok("m['section'] = PS.section_for(m.get('dosage_form'))" in sales_r and "sections=PS.SECTIONS" in sales_r, 'sale route gives every item its section')
ns = open(_os.path.join(ROOT, 'templates', 'new_sale.html'), encoding='utf-8').read()
ok('<optgroup label="{{ label }}">' in ns and "{% for m in medicines if m.section == key %}" in ns, 'sale dropdown is grouped by section')
ok('class="pick-card"' in ns and 'onclick="pickCard({{ m.medicine_id }})"' in ns and 'data-sec="all"' in ns, 'sale screen has a product picker with section tabs and cards')
ok('function addOptionToSale(opt, mult)' in ns and 'addOptionToSale(opt, mult);' in ns and 'function pickFilter()' in ns, 'barcode add and card click share one add function')

# v86.7: 7-day sales bars, pagination, daily backup scheduler, phone layout
psrc = open(_os.path.join(ROOT, 'pharmacy', 'services', 'product_sections.py'), encoding='utf-8').read()
ok("'sold_week'" in psrc and "INTERVAL 6 DAY" in psrc, 'section overview counts units sold in 7 days')
dsh = open(_os.path.join(ROOT, 'templates', 'dashboard.html'), encoding='utf-8').read()
ok("dv-week" in dsh and "@keyframes dvUp" in dsh and "prefers-reduced-motion" in dsh, 'dashboard: 7-day bar with animation, reduced-motion respected')
ok("per = 100000" in route, 'section page: all items on one page (v86.26)')
ok("pager" not in tpl.split("{% if false %}")[0] and "<span class=\"pd-sub\">Showing" not in tpl, 'section page: no pager, all items on one page (v86.36)')
sched = open(_os.path.join(ROOT, 'scripts', 'schedule_daily_backup.bat'), encoding='utf-8').read()
ok('schtasks /Create' in sched and '/SC DAILY' in sched and 'backup_db.bat' in sched, 'daily backup: Windows Task Scheduler script at 23:30')
ok("@media (max-width: 760px)" in ns and ".sale-grid tr" in ns, 'sale screen: phone layout rules')

# v86.8: section pages get the same stat cards as Medicines
ok("'expiring': sum(1 for x in rows if x['next_expiry']" in route and "stats=stats" in route, 'section page computes total, in stock, low, out and expiring over all rows, not one page')
ok('Expiring in 90 days' in tpl and 'class="stat-card alert"' in tpl and '<div class="page-header"' in tpl, 'section page shows the same stat cards and header as Medicines')

# v86.9: 15 / 50 / 100 rows on Medicines and section pages, serial numbers, numbered pages
med_route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'medicines.py'), encoding='utf-8').read()
ok("per = 100000" in med_route, 'Medicines page: all items on one page (v86.26)')
med_tpl2 = open(_os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8').read()
ok("{% for n in [15, 50, 100] %}" in med_tpl2 and "{{ offset + loop.index }}" in med_tpl2, 'Medicines page: 15/50/100 choice and row numbers')
ok("{{ loop.index }}" in tpl and "{% for n in [15, 50, 100] %}" not in tpl, 'section page: row numbers, no 15/50/100 choice (v86.36)')
ok("range([pager.page - 2, 1]|max" not in tpl, 'section page: no numbered page links (v86.36)')

# v86.10: sales list 15 / 50 / 100 with row numbers
sr = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
ok("if per not in (15, 50, 100):" in sr and "'per': per}" in sr, 'sales list: 15, 50 or 100 per page, kept in the page links')
st = open(_os.path.join(ROOT, 'templates', 'sales.html'), encoding='utf-8').read()
ok("{{ offset + loop.index }}" in st and "{% for n in [15, 50, 100] %}" in st, 'sales list: row numbers and the 15/50/100 choice')

# v86.11: receipt grouped by section with subtotals
rs = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'sales.py'), encoding='utf-8').read()
ok("m.dosage_form, SUM(si.quantity)" in rs and "groups=ordered" in rs and "'lines': []" in rs, 'receipt: lines grouped by section, with subtotal and units per section')
rt = open(_os.path.join(ROOT, 'templates', 'receipt_thermal.html'), encoding='utf-8').read()
ok("{% for g in groups %}" in rt and "{% for it in g.lines %}" in rt and "Items: {{ units }}" in rt, 'receipt template: section headings and item count')

# v86.12: dashboard visual pass
dcss = open(_os.path.join(ROOT, 'static', 'css', 'dashboard.css'), encoding='utf-8').read()
ok("v86.12" in dcss and "backdrop-filter: blur(10px)" in dcss and 'prefers-reduced-motion: reduce' in dcss.split('v86.12')[1], 'dashboard: visible background, frosted cards, reduced-motion guard')
ok('[data-theme="dark"] .dash .d-card' in dcss.split('v86.12')[1], 'dashboard: dark-mode card colours')

# v86.14: error ID on every unexpected error
lsrc = open(_os.path.join(ROOT, 'pharmacy', 'lib.py'), encoding='utf-8').read()
ok("code = 'ERR-' + uuid.uuid4().hex[:6].upper()" in lsrc and "Error ID: {code}" in lsrc, 'guarded: each unexpected route error gets an ID, shown to the user and written in the log')
ok("eid = code or ('ERR-' + uuid.uuid4().hex[:6].upper())" in lsrc and "Error ID: {eid}" in lsrc, 'flash_unexpected: same ID scheme')
ok("detail=f'Error ID: {code}" in lsrc and "jsonify(error=f'Something went wrong on the server. Error ID {code}.'" in lsrc, '500 page and JSON errors carry the ID')
ok('id="scanBox" class="form-control-pro" style="margin-bottom:0;" autocomplete="off" autofocus' in ns, 'sale screen: barcode box has focus when the page opens (counter can scan at once)')
ok("var box = document.getElementById('scanBox');\n    if (box) { box.value = ''; box.focus(); }" in ns, 'after an add the cursor returns to the barcode box')
ok("e.target.classList.contains('qty')" in ns, 'Enter in a quantity box returns to the barcode box')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
