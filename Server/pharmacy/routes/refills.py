"""Routes: Refill Reminders (v97) — mahana dawai walay customers ki due list."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services.refills import due_refills


@app.route('/refills')
@login_required
@guarded
def refills():
    cur = mysql.connection.cursor()
    rows = due_refills(cur)
    cur.close()
    return render_template('refills.html', rows=rows, shop=get_setting('shop_name') or 'MediGen Pharmacy')
