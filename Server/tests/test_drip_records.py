"""v85: drip and injection records, expiry and the dashboard tile. No MySQL. Run through tests/run_all.py."""
import os as _os, sys, datetime as _dt
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import drip_report as RPT
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

class Cur:
    """Answers by SQL text. Tables are plain lists in self.data."""
    def __init__(self, data):
        self.data, self.rows, self.sqls = data, [], []
    def execute(self, sql, params=()):
        self.sqls.append(sql)
        q = ' '.join(sql.split())
        if q.startswith('SELECT medicine_id, dosage_form FROM medicines'):
            self.rows = self.data['meds']
        elif q.startswith('SELECT medicine_id, stock_quantity, reorder_level'):
            self.rows = self.data['stock']
        elif 'FROM batches' in q and 'COUNT(*)' in q:
            self.rows = [{'n': self.data['expiring']}]
        elif 'FROM batches' in q and 'SUM(quantity)' in q:
            self.rows = [{'q': self.data['expired_qty']}]
        elif 'FROM drip_injections' in q and 'COUNT(*) AS n, IFNULL(SUM' in q:
            self.rows = [{'n': self.data['today_n'], 'q': self.data['today_q']}]
        elif 'FROM drip_injections' in q and 'MONTH' in q:
            self.rows = [{'n': self.data['month_n']}]
        elif 'FROM batches b JOIN medicines' in q:
            self.rows = self.data['expiry']
        elif 'FROM drip_injections d' in q:
            self.rows = self.data['records']
        else:
            self.rows = []
    def fetchone(self):
        return self.rows[0] if self.rows else None
    def fetchall(self):
        return list(self.rows)

DATA = {
    'meds': [{'medicine_id': 1, 'dosage_form': 'Injection'}, {'medicine_id': 2, 'dosage_form': 'Drip / IV fluid'},
             {'medicine_id': 3, 'dosage_form': 'Tablet'}],
    'stock': [{'medicine_id': 1, 'stock_quantity': 10, 'reorder_level': 20}, {'medicine_id': 2, 'stock_quantity': 0, 'reorder_level': 5}],
    'expiring': 3, 'expired_qty': 7, 'today_n': 4, 'today_q': 6, 'month_n': 19,
    'expiry': [{'name': 'Ceftriaxone', 'batch_number': 'B1', 'expiry_date': _dt.date(2026, 12, 1), 'quantity': 5, 'days_left': 30},
               {'name': 'Dextrose', 'batch_number': 'B2', 'expiry_date': _dt.date(2026, 10, 1), 'quantity': 2, 'days_left': -20}],
    'records': [{'given_at': _dt.datetime(2026, 10, 26, 9, 5), 'medicine_name': 'Ceftriaxone', 'quantity': 2}],
}

s = RPT.summary(Cur(DATA))
ok(s['items'] == 2 and s['in_stock'] == 1 and s['no_stock'] == 1, 'summary counts drip items only (tablet ignored), in stock and no stock')
ok(s['low_stock'] == 1, 'low stock = in stock and at or below reorder level')
ok(s['expiring'] == 3 and s['expired_qty'] == 7 and s['expiring_window'] == 90, 'summary expiry numbers come from batches with stock')
ok(s['today_records'] == 4 and s['today_qty'] == 6 and s['month_records'] == 19, 'summary records today and this month')

exp = RPT.expiring_batches(Cur(DATA))
ok(len(exp) == 2 and exp[0]['days_left'] == 30, 'expiring list returns batches with stock, expired ones included')
ok(RPT.expiring_batches(Cur(dict(DATA, meds=[{'medicine_id': 3, 'dosage_form': 'Tablet'}]))) == [], 'no drip items means an empty expiry list')

recs = RPT.records(Cur(DATA), _dt.date(2026, 10, 1), _dt.date(2026, 10, 31))
ok(len(recs) == 1 and recs[0]['medicine_name'] == 'Ceftriaxone', 'records query returns the rows in the range')

src = open(_os.path.join(ROOT, 'pharmacy', 'services', 'drip_report.py'), encoding='utf-8').read()
ok('INTERVAL {EXPIRY_WINDOW_DAYS} DAY' in src and 'INTERVAL %s DAY' in src, 'expiry windows are written as plain SQL with safe parameters')
rt = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'drip.py'), encoding='utf-8').read()
ok("'/drip/records'" in rt and "_csv_response(header, data" in rt and "d_to - d_from" in rt, 'records page has date range, CSV export and a one-year limit')
ok('RPT.summary(cur)' in open(_os.path.join(ROOT, 'pharmacy', 'routes', 'dashboard.py'), encoding='utf-8').read(), 'dashboard calls the drip summary')
dash = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'dashboard.py'), encoding='utf-8').read()
ok('except Exception' in dash.split('RPT.summary(cur)')[1][:200], 'a failing drip summary cannot break the dashboard')
dt = open(_os.path.join(ROOT, 'templates', 'dashboard.html'), encoding='utf-8').read()
ok('{% if drip %}' in dt and "url_for('drip_records')" in dt, 'dashboard shows the drip tile with a link to records')
rec_t = open(_os.path.join(ROOT, 'templates', 'drip_records.html'), encoding='utf-8').read()
ok('Download CSV' in rec_t and 'Expired stock is not sold' in rec_t, 'records template has CSV download and the expiry note')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
