"""Routes: daily closing and customer dues (with WhatsApp reminders). SQL in pharmacy/repos/business.py."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _valid_date
from pharmacy.repos import business as repo
from pharmacy.business_rules import udhaar_message, whatsapp_link


@app.route('/daily-closing')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def daily_closing():
    day = _valid_date(request.args.get('date', '')) or date.today().isoformat()
    cur = mysql.connection.cursor()
    data = repo.daily_closing(cur, day)
    cur.close()
    received = sum(data['by_method'].values())
    data['received'] = received
    data['net'] = received - data['refunds']
    return render_template('closing.html', day=day, c=data, methods=PAY_METHODS,
                           shop=get_setting('shop_name'), today=date.today().isoformat())


@app.route('/customer-dues')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def customer_dues():
    cur = mysql.connection.cursor()
    rows = repo.customers_with_dues(cur)
    cur.close()
    shop = get_setting('shop_name')
    total = 0.0
    for r in rows:
        due = float(r['due'] or 0)
        total += due
        r['due'] = due
        msg = udhaar_message(r['name'], due, shop)
        r['wa_link'] = whatsapp_link(r['contact_number'], msg)
    return render_template('customer_dues.html', rows=rows, total=total, shop=shop)
