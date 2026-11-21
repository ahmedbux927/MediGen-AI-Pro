"""Routes: Owner summary, a phone-friendly one-screen view for the Admin (v86.49). Read only."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.repos import business as biz_repo
from pharmacy.repos import supplier_ledger as sup_repo


@app.route('/owner')
@login_required
@role_required('Admin')
@guarded
def owner_home():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT COUNT(*) AS n, IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
                   FROM sales WHERE DATE(sale_date) = CURDATE()""")
    today = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS n FROM v_low_stock")
    low = int(cur.fetchone()['n'] or 0)
    cur.execute("SELECT COUNT(*) AS n FROM v_expiring_soon")
    expiring = int(cur.fetchone()['n'] or 0)
    cur.execute("SELECT COUNT(*) AS n FROM purchase_orders WHERE status = 'Pending'")
    pending_po = int(cur.fetchone()['n'] or 0)
    dues = biz_repo.customers_with_dues(cur)
    dues_total = sum(float(r['due'] or 0) for r in dues)
    sups = sup_repo.supplier_totals(cur)
    returns = sup_repo.returns_by_supplier(cur)
    paid = sup_repo.paid_by_supplier(cur)
    cur.close()
    owed = 0.0
    for s in sups:
        owed += float(s['bought'] or 0) - returns.get(s['supplier_id'], 0.0) - paid.get(s['supplier_id'], 0.0)
    return render_template('owner_home.html', today_count=int(today['n'] or 0),
                           today_revenue=float(today['revenue'] or 0), low=low, expiring=expiring,
                           pending_po=pending_po, dues_count=len(dues), dues_total=dues_total,
                           supplier_owed=owed, shop=get_setting('shop_name'))
