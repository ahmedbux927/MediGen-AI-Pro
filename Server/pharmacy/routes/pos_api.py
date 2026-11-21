"""Routes: POS checkout for the barcode scanner and the mobile app (v54).

POST /api/pos/checkout   Authorization: Bearer <token>   JSON body
  {"items": [{"barcode": "8901...", "quantity": 2}, {"medicine_id": 5}],
   "payment_method": "Cash", "customer_id": null, "discount": 0, "discount_type": "amount",
   "paid": null, "prescription_id": null}
  201 -> {"sale_id", "total", "paid", "balance"}
  400 -> {"error": "..."} (a problem the cashier can fix)
  409 -> the same bill was sent again within seconds: nothing saved twice
  403 -> token not linked to a user (create it with a username)
"""
from flask import g, jsonify, request
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.routes.api import api_required
from pharmacy.services import pos
from pharmacy.services.sales import BillError


@app.route('/api/pos/checkout', methods=['POST'])
@api_required('Admin', 'Pharmacist')
@guarded
def pos_checkout():
    tok = g.api_token
    user_id = tok.get('user_id')
    if not user_id:
        return jsonify(error='This token is not linked to a user. Create it with a username '
                             '(scripts/create_api_token.py).'), 403
    body = request.get_json(silent=True)
    username = 'api:' + (tok.get('label') or 'token')[:60]
    cur = mysql.connection.cursor()

    def audit_fn(cur_, action, entity, entity_id, details, before=None, after=None, status='ok'):
        audit_as(cur_, user_id, username, action, entity, entity_id, details, before, after, status)

    try:
        offline_sync = bool(request.headers.get('X-Offline-Sync'))   # v87.21: phone sync sends this header
        result = pos.checkout(cur, user_id, tok['role'], body, get_tax_rate(),
                              get_cashier_max(), audit_fn, offline_sync=offline_sync)
        mysql.connection.commit()
        return jsonify(result), 201
    except pos.DuplicateBill as e:
        mysql.connection.rollback()
        return jsonify(error=str(e)), 409
    except BillError as e:
        mysql.connection.rollback()
        return jsonify(error=str(e)), 400
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('POS checkout failed [%s]', ERROR_CODES['api_checkout'])
        return jsonify(error=f"Checkout failed. Error {ERROR_CODES['api_checkout']}. Check the log."), 500
    finally:
        cur.close()
