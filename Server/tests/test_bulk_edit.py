"""v86.41: Edit selected (bulk edit) and the Receive stock popup. Static checks of the code paths.
Run through tests/run_all.py, or directly: python tests/test_bulk_edit.py"""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))
def read(rel): return open(_os.path.join(ROOT, *rel.split('/')), encoding='utf-8').read()

route = read('pharmacy/routes/medicines.py')
repo = read('pharmacy/repos/medicines.py')
ok("@app.route('/medicines/bulk-edit', methods=['POST'])" in route and "role_required('Admin', 'Pharmacist')" in route.split('def bulk_edit_medicines')[0].split('@app.route')[-1],
   'bulk edit route exists and is for Admin and Pharmacist only')
body = route.split('def bulk_edit_medicines')[1].split('@app.route')[0]
ok("if not (cat_raw or form_raw or price_raw or exp_raw or strength)" in body, 'blank form changes nothing')
ok("name=\"strength\"" in read('templates/_bulk_edit.html') and "repo.bulk_update_expiry" in body, 'strength field in popup and expiry goes through repo')
ok("if form_raw not in set(MEDICINE_FORMS) | set(PS.ALL_FORM_CHOICES)" in body, 'dosage form must be from the list')
ok("price < 0" in body, 'negative price is refused')
ok("audit(cur, 'medicine.bulk_edit'" in body, 'bulk edit is written to the audit log')
ok("back.startswith('/medicines') or back.startswith('/products/')" in body, 'return page is limited to medicine pages (no open redirect)')
ok("def bulk_update_fields" in repo and "is_deleted = 0 AND medicine_id IN" in repo, 'field update skips deleted items')
ok("UPDATE batches SET expiry_date" in repo, 'expiry change updates every batch of the chosen items')
ok("'name=\"expiry\"'" in "" or 'name="expiry"' in read('templates/_bulk_edit.html'), 'popup has an expiry date field')
ok('name="category_id"' in read('templates/_bulk_edit.html') and 'name="dosage_form"' in read('templates/_bulk_edit.html'),
   'popup has category and dosage form fields')
ok("{% include '_bulk_edit.html' %}" in read('templates/medicines.html') and "{% include '_bulk_edit.html' %}" in read('templates/products.html'),
   'Medicines and section pages both use the same popup')
ok('onclick="openBulkEdit()"' in read('templates/medicines.html') and 'onclick="openBulkEdit()"' in read('templates/products.html'),
   'Edit selected button is in both bulk bars')
prod = read('templates/products.html')
ok('id="receiveModal"' in prod and 'id="receive"' not in prod, 'Receive stock is a popup, not a card at the bottom')
ok("openReceive({{ r.medicine_id }})" in prod and "function openReceive" in prod, 'row receive icon opens the popup with that item chosen')

if __name__ == '__main__':
    fails = [m for m, good in RESULTS if not good]
    for m, good in RESULTS:
        print(('PASS ' if good else 'FAIL ') + m)
    print(f"\nTOTAL: {len(RESULTS)-len(fails)} passed, {len(fails)} failed")
