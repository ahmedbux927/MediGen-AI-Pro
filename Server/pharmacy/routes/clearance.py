"""Routes: Expiry Clearance (v97) — khatam honay walay batches ki amal list:
kitne din baqi, kitni rakam phansi hui hai, aur discount ki tajweez (sirf tajweez —
rate khud nahi badalta)."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from datetime import date


def _suggestion(days_left):
    if days_left < 0:
        return 'Expired — sale rokein, supplier return ki koshish karein'
    if days_left <= 30:
        return '15% off laga kar pehle bechne ki koshish (tajweez)'
    if days_left <= 60:
        return '10% off tajweez — pehle ye batch bechein'
    return '5% off tajweez ya aam rate par pehle ye batch'


@app.route('/expiry-clearance')
@login_required
@guarded
def expiry_clearance():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT m.name, m.price, b.batch_number, b.expiry_date, b.quantity
                   FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0 AND b.quantity > 0
                     AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)
                     AND b.expiry_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                   ORDER BY b.expiry_date, m.name""")
    rows = cur.fetchall()
    cur.close()
    today = date.today()
    total_value = 0.0
    for r in rows:
        r['days_left'] = (r['expiry_date'] - today).days
        r['value'] = float(r['quantity'] or 0) * float(r['price'] or 0)
        r['suggestion'] = _suggestion(r['days_left'])
        total_value += r['value']
    return render_template('clearance.html', rows=rows, total_value=total_value)
