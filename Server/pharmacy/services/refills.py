"""Refill reminders (v97): jin customers ne wahi dawai baar baar li hai, unke
kharidari ke waqfay se andaaza lagta hai ke agli dawai kab due hai. Ye ek
andaaza hai (unke apne pattern par), koi medical hidayat nahi."""
from datetime import date


def _wa_number(raw):
    d = ''.join(ch for ch in (raw or '') if ch.isdigit())
    if d.startswith('0'):
        d = '92' + d[1:]
    return d


def due_refills(cur, today=None):
    """Due window: due date guzray 14 din tak, ya anay walay 10 din ke andar."""
    today = today or date.today()
    cur.execute("""SELECT c.customer_id, c.name, c.contact_number, m.name AS med_name,
                          DATE(s.sale_date) AS buy_date, si.quantity
                   FROM sales s
                   JOIN sale_items si ON si.sale_id = s.sale_id
                   JOIN customers c ON c.customer_id = s.customer_id
                   JOIN medicines m ON m.medicine_id = si.medicine_id
                   WHERE s.customer_id IS NOT NULL AND c.name <> 'Walk-in'
                     AND s.sale_date >= DATE_SUB(CURDATE(), INTERVAL 180 DAY)
                   ORDER BY c.customer_id, m.medicine_id, s.sale_date""")
    groups = {}
    for r in cur.fetchall():
        key = (r['customer_id'], r['med_name'])
        g = groups.setdefault(key, {'customer_id': r['customer_id'], 'name': r['name'],
                                    'contact_number': r['contact_number'], 'med_name': r['med_name'],
                                    'dates': [], 'last_qty': 0})
        if not g['dates'] or g['dates'][-1] != r['buy_date']:
            g['dates'].append(r['buy_date'])
        g['last_qty'] = r['quantity']
    out = []
    for g in groups.values():
        dates = g['dates']
        if len(dates) < 2:
            continue
        gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
        gaps = [x for x in gaps if x > 0]
        if not gaps:
            continue
        avg_gap = round(sum(gaps) / len(gaps))
        from datetime import timedelta
        due = dates[-1] + timedelta(days=avg_gap)
        days_left = (due - today).days
        if -14 <= days_left <= 10:
            out.append({'name': g['name'], 'contact_number': g['contact_number'],
                        'wa': _wa_number(g['contact_number']), 'med_name': g['med_name'],
                        'last_buy': dates[-1], 'last_qty': g['last_qty'], 'buys': len(dates),
                        'avg_gap': avg_gap, 'due': due, 'days_left': days_left})
    out.sort(key=lambda x: x['days_left'])
    return out
