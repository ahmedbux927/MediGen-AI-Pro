"""Routes: find a customer by phone while billing (v73 quick-pick)."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.services import phone_search as PS


@app.route('/customers/search')
@guarded
def customers_search():
    """JSON list for the POS phone box. Too few digits -> empty list."""
    if 'user_id' not in session:
        return jsonify({'error': 'Session expired. Please login again.'}), 401
    cur = mysql.connection.cursor()
    try:
        rows = PS.search_customers(cur, request.args.get('phone', ''), 8)
    finally:
        cur.close()
    return jsonify([{'customer_id': r['customer_id'], 'name': r['name'],
                     'contact': r['contact_number'] or '', 'balance': float(r['balance'] or 0)} for r in rows])
