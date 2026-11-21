"""Daily inventory report (backend track, B7). Run it from Windows Task Scheduler every morning.

    python scripts/inventory_report.py                 # writes reports/YYYY-MM-DD/ next to the project
    python scripts/inventory_report.py --out D:\\reports

Writes four CSV files (opens in Excel) and prints a short summary:
  expiry_buckets.csv, low_stock.csv, purchase_suggestions.csv, summary.txt
It only reads the database. Nothing is changed. Exit code 0 = done.
"""
import argparse
import csv
import os
import sys
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services.inventory import expiry_buckets, low_stock, purchase_suggestions  # noqa: E402


def write_csv(path, header, rows):
    with open(path, 'w', newline='', encoding='utf-8-sig') as fh:      # BOM so Excel shows names correctly
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', help='folder for the reports (default: reports/YYYY-MM-DD in the project)')
    args = ap.parse_args()
    today = date.today()
    out = args.out or os.path.join(ROOT, 'reports', today.isoformat())
    os.makedirs(out, exist_ok=True)

    import app as A
    with A.app.app_context():
        cur = A.mysql.connection.cursor()
        try:
            cur.execute("""SELECT m.medicine_id, m.name, b.batch_number, b.expiry_date, b.quantity
                           FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                           WHERE b.quantity > 0 AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)""")
            batches = cur.fetchall()
            cur.execute("SELECT medicine_id, name, stock_quantity, reorder_level, cost_price FROM medicines")
            medicines = cur.fetchall()
            cur.execute("""SELECT pi.medicine_id, po.supplier_id, s.name AS supplier_name
                           FROM purchase_items pi
                           JOIN purchase_orders po ON po.po_id = pi.po_id
                           JOIN suppliers s ON s.supplier_id = po.supplier_id
                           WHERE po.status = 'Received'
                           ORDER BY po.order_date DESC, pi.po_item_id DESC""")
            history = cur.fetchall()
            try:                              # Phase 4: cold-chain readings out of range in the last 24 hours
                cur.execute("""SELECT location, temperature_c, recorded_at FROM temperature_logs
                               WHERE in_range = 0 AND recorded_at >= NOW() - INTERVAL 1 DAY
                               ORDER BY recorded_at""")
                cold_alerts = cur.fetchall()
            except Exception:                 # table missing (migration 006 not applied yet)
                cold_alerts = None
        finally:
            cur.close()

    buckets = expiry_buckets(batches, today)
    low = low_stock(medicines)
    last_supplier = {}
    for r in history:                                  # newest first: keep the first one per medicine
        last_supplier.setdefault(r['medicine_id'], (r['supplier_id'], r['supplier_name']))
    suggestions = purchase_suggestions(low, last_supplier)

    write_csv(os.path.join(out, 'expiry_buckets.csv'), ['bucket', 'medicine', 'batch', 'expiry', 'days_left', 'quantity'],
              [[b, r['name'], r['batch_number'], r['expiry_date'], r['days_left'], r['quantity']]
               for b, rows in buckets.items() for r in rows])
    write_csv(os.path.join(out, 'low_stock.csv'), ['severity', 'medicine', 'stock', 'reorder_level'],
              [[r['severity'], r['name'], r['stock_quantity'], r['reorder_level']] for r in low])
    write_csv(os.path.join(out, 'purchase_suggestions.csv'),
              ['supplier', 'medicine', 'stock', 'reorder_level', 'order_qty', 'unit_cost', 'line_cost'],
              [[g['supplier'], i['name'], i['stock'], i['reorder_level'], i['order_qty'], i['unit_cost'], i['line_cost']]
               for g in suggestions.values() for i in g['items']])
    summary = [f'Inventory report {today.isoformat()}',
               *[f'{k}: {len(v)} batch(es)' for k, v in buckets.items()],
               f"out of stock: {sum(1 for r in low if r['severity'] == 'out')}",
               f"critical (below half reorder level): {sum(1 for r in low if r['severity'] == 'critical')}",
               f"low (at reorder level): {sum(1 for r in low if r['severity'] == 'low')}",
               f"suggested order value (estimate, at cost): {sum(g['estimated_cost'] for g in suggestions.values()):,.2f}",
               f"suppliers with suggestions: {len(suggestions)}",
               *(['cold chain: temperature log not available yet'] if cold_alerts is None else
                 [f'cold chain: {len(cold_alerts)} reading(s) out of range in the last 24 hours']
                 + [f"  {r['location']} {r['temperature_c']} C at {r['recorded_at']}" for r in cold_alerts])]
    with open(os.path.join(out, 'summary.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(summary) + '\n')
    print('\n'.join(summary))
    print('Reports written to:', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
