"""Controlled schedule on the product edit page (v87.08): wiring and warning checks. No MySQL needed.
Run: python tests/test_schedule_field.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, ROOT)

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()

src = read('pharmacy/routes/products.py')
ok("schedule = (request.form.get('schedule') or '').strip()[:20] or None" in src, 'edit reads the schedule, trimmed to 20 characters, blank means none')
ok('schedule=%s, units_per_pack=%s WHERE medicine_id=%s' in src and 'name, strength, form, price, reorder, barcode, schedule, units_per_pack, mid' in src,
   'the schedule is saved in the same UPDATE as the other fields')
ok("schedule {schedule or 'none'}" in src, 'the activity log records the schedule')
tpl = read('templates/products_edit.html')
ok('name="schedule"' in tpl and "med.schedule or ''" in tpl, 'edit form shows and posts the schedule')
ok('every sale of this medicine needs a prescription attached' in tpl, 'form warns that a schedule forces a prescription on every sale')
ok('Controlled schedule (leave blank if not controlled)' in tpl, 'label says blank means not controlled')
ok('e.g. H or G' in tpl and 'as your drug authority names it' in tpl, 'the shop types the schedule name its authority uses (no invented categories)')

sales = read('pharmacy/services/sales.py')
ok('def check_scheduled' in sales and 'scheduled_items(cur' in sales, 'sales already require a prescription for scheduled medicines (unchanged)')
ok("if r.get('schedule')" in read('pharmacy/services/controlled_register.py'),
   'the register rule reads the schedule set here')

import py_compile
try:
    py_compile.compile(os.path.join(ROOT, 'pharmacy/routes/products.py'), doraise=True); ok(True, 'products route compiles')
except py_compile.PyCompileError as e:
    ok(False, 'products route compiles: %s' % e)

print(f'{PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
