"""Routes: Daily Digest (v96) — the owner's one-page morning summary:
yesterday's sales, low stock, expiring batches, customer dues (with one-click
WhatsApp reminders) and the health of the automatic backup. Admin only."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.repos import business as biz_repo
from pharmacy.services.refills import due_refills
from urllib.parse import quote as _urlquote


def _wa_number(raw):
    """Local 03xx number ko international 92xx form me (invoice share jaisa hi rule)."""
    d = ''.join(ch for ch in (raw or '') if ch.isdigit())
    if d.startswith('0'):
        d = '92' + d[1:]
    return d


@app.route('/digest')
@login_required
@role_required('Admin')
@guarded
def daily_digest():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
                   FROM sales WHERE DATE(sale_date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)""")
    yday = cur.fetchone()
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
                   FROM sales WHERE DATE(sale_date) = CURDATE()""")
    today = cur.fetchone()
    cur.execute("""SELECT name, stock_quantity, reorder_level FROM medicines
                   WHERE is_deleted = 0 AND stock_quantity <= reorder_level
                   ORDER BY stock_quantity, name LIMIT 10""")
    low = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS n FROM v_low_stock")
    low_total = int(cur.fetchone()['n'] or 0)
    cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity
                   FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0 AND b.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 90 DAY)
                   ORDER BY b.expiry_date, m.name LIMIT 10""")
    exp = cur.fetchall()
    cur.execute("SELECT COUNT(*) AS n FROM v_expiring_soon")
    exp_total = int(cur.fetchone()['n'] or 0)
    dues = biz_repo.customers_with_dues(cur)
    refills = due_refills(cur)
    cur.close()
    for r in dues:
        r['wa'] = _wa_number(r.get('contact_number'))
    dues_total = sum(float(r['due'] or 0) for r in dues)
    backup = backup_status()
    shop = get_setting('shop_name') or 'MediGen Pharmacy'
    lines = [f"{shop} — Daily Digest",
             f"Yesterday: {int(yday['n'] or 0)} bills, Rs {float(yday['revenue'] or 0):,.0f}",
             f"Low stock: {low_total} items",
             f"Expiring within 90 days: {exp_total} batches",
             f"Customer dues: Rs {dues_total:,.0f} ({len(dues)} customers)",
             ("Backup: OK — " + backup['when']) if backup['exists'] and not backup['stale']
             else "Backup: WARNING — no recent backup!"]
    wa_text = _urlquote('\n'.join(lines))
    owner_wa = _wa_number(get_setting('owner_whatsapp') or '')
    return render_template('digest.html', yday=yday, today=today, low=low, low_total=low_total,
                           exp=exp, exp_total=exp_total, dues=dues[:10], dues_total=dues_total,
                           dues_count=len(dues), backup=backup, wa_text=wa_text, owner_wa=owner_wa, refills=refills,
                           shop=shop)
