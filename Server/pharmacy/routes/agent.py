"""Routes: AI agent confirmation. The chat proposes a change; only this route saves it, and only for the same user."""
from datetime import datetime

from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import audit
from pharmacy.services import agent_tools as AT


@app.route('/agent/confirm', methods=['POST'])
@guarded
def agent_confirm():
    if 'user_id' not in session:
        return jsonify({'error': 'Session expired. Please login again.'}), 401
    if session.get('role') not in ('Admin', 'Pharmacist'):
        return jsonify({'error': 'Only Admin or Pharmacist can change data.'}), 403
    data = request.get_json(silent=True) or {}
    cur = mysql.connection.cursor()
    try:
        AT.ensure_agent_table(cur)
        res = AT.confirm(cur, session['user_id'], data.get('token'), datetime.now(), audit)
        mysql.connection.commit()
        return jsonify({'answer': _agent_done_text(res)})
    except AT.AgentError as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('agent confirm failed')
        return jsonify({'error': 'Change could not be saved. Nothing was changed.'}), 500
    finally:
        cur.close()


def _agent_done_text(res):
    if res['action'] == 'set_shelf_location':
        return f"Done. Shelf location saved: {res['result']['shelf_location']}."
    return f"Done. Customer added (#{res['result']['customer_id']})."
