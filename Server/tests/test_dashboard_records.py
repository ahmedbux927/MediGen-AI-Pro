"""v86.76: per-section dashboard records (pharmacy/services/dashboard_records.py). Fake cursor, no MySQL."""
import os as _os, sys as _sys, types as _types
from datetime import date, datetime
from decimal import Decimal as D
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
_sys.path.insert(0, ROOT)
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

TODAY = date(2026, 10, 29)
class FakeCur:
    """Answers each query by a keyword in the SQL text."""
    def __init__(self): self.rows = []; self.sql = ''
    def execute(self, sql, params=None): self.sql = ' '.join(sql.split()); self.params = params
    def fetchall(self):
        s = self.sql
        if 'FROM medicines' in s and 'SELECT medicine_id, dosage_form' in s:
            return [dict(medicine_id=1, dosage_form='Tablet', stock_quantity=60, reorder_level=10),
                    dict(medicine_id=2, dosage_form='Syrup', stock_quantity=0, reorder_level=5),
                    dict(medicine_id=3, dosage_form='Cream', stock_quantity=3, reorder_level=5)]
        if 'stock_quantity <= reorder_level' in s:
            return [dict(name='Cream X', dosage_form='Cream', stock_quantity=3, reorder_level=5)]
        if 'FROM batches b' in s:
            return [dict(name='Panadol', dosage_form='Tablet', batch_number='B1', expiry_date=date(2026, 11, 15), quantity=20)]
        if 'HAVING sold > 0' in s:
            return [dict(name='Panadol', dosage_form='Tablet', sold=D('7'), revenue=D('700'))]
        if 'FROM sale_items si' in s and 'GROUP BY m.dosage_form, s.customer_id' in s:
            return [dict(dosage_form='Tablet', customer_id=4), dict(dosage_form='Tablet', customer_id=5), dict(dosage_form='Syrup', customer_id=4)]
        if 'FROM sales WHERE' in s:
            return [dict(d=TODAY, rev=D('700'))]
        if 'FROM purchase_items' in s and 'GROUP BY' in s:
            return [dict(d=TODAY, amt=D('300'))]
        if 'FROM purchase_items' in s:
            return [dict(dosage_form='Tablet', order_date=TODAY, quantity=D('10'), unit_price=D('30'))]
        return []
    def fetchone(self): return None

# _section_rows comes from reports; give it a stub so the test does not need the whole app
_rep = _types.ModuleType('pharmacy.routes.reports')
def _section_rows(cur, start, end):
    from pharmacy.services import product_sections as PS
    rows = {k: {'key': k, 'sold': 0, 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0} for k in PS.SECTION_KEYS}
    if str(start) == TODAY.isoformat():
        rows['medicines'].update(sold=7, revenue=700.0, cost=210.0, profit=490.0)
    else:
        rows['medicines'].update(sold=40, revenue=4000.0, cost=2000.0, profit=2000.0)
    return list(rows.values())
_rep._section_rows = _section_rows
_sys.modules['pharmacy.routes.reports'] = _rep

from pharmacy.services import dashboard_records as DR
cur = FakeCur()
rec = DR.build(cur, TODAY)
secs = {s['key']: s for s in rec['sections']}
ok(list(secs) == ['medicines', 'syrups', 'creams', 'drip', 'other'], 'five sections in the order of the product sections')
ok(secs['medicines']['items'] == 1 and secs['syrups']['out'] == 1 and secs['creams']['low'] == 1, 'stock counts come from the shared overview')
ok(secs['medicines']['sold_today'] == 7 and secs['medicines']['profit_today'] == 490.0, 'sold and profit today per section')
ok(secs['medicines']['sales_month'] == 4000.0 and secs['medicines']['profit_month'] == 2000.0, 'month sales and profit per section')
ok(secs['medicines']['purchase_today'] == 300.0 and secs['medicines']['purchase_month'] == 300.0, 'purchases today and month per section (order_date = today)')
ok(secs['medicines']['customers_month'] == 2 and secs['syrups']['customers_month'] == 1, 'customers per section are distinct')
ok(secs['medicines']['expiring'] == 1 and secs['medicines']['expiring_items'][0]['days'] == 17, 'expiring batch in 90 days, days left counted')
ok(secs['medicines']['top'][0]['sold'] == 7, 'best seller of the section')
ok(secs['creams']['low_items'][0]['name'] == 'Cream X', 'low stock item is listed under its section')
ok(rec['totals']['sold_today'] == 7 and rec['totals']['customers_month'] == 2, 'shop totals add the sections, customers are not double counted')
ok(len(rec['week']['days']) == 7 and rec['week']['days'][-1] == '29 Oct', 'last 7 days end today (12 AM restart by date)')
ok(rec['week']['sales'][-1] == 700.0 and rec['week']['purchases'][-1] == 300.0, 'daily sales and purchases for the chart')
ok(rec['day'] == '2026-10-29', 'day is the shop date passed in')
ok(secs['medicines']['customers_all'] == 2 and rec['totals']['customers_all'] == 2, 'customers all time are counted separately from this month')
ok('no_price' in secs['medicines'] and 'no_price' in rec['totals'], 'items with price 0 are counted per section for the dashboard')
print_fail = [m for m, c in RESULTS if not c]
if __name__ == '__main__':
    for m, c in RESULTS: print(('PASS ' if c else 'FAIL ') + m)
    print(f'TOTAL: {len(RESULTS)-len(print_fail)} passed, {len(print_fail)} failed')
