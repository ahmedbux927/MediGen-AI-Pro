"""Routes: chatbot."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _chat_reply, _ensure_chat_table
from datetime import datetime
from pharmacy.services import agent_router as AR
from pharmacy.services import agent_tools as AT
from pharmacy.services import ai_pro as AIP

AGENT_ROLES = ('Admin', 'Pharmacist')

# Stage 6: per-user rate limit + a 10-minute answer cache for repeated questions.
_limiter = AIP.RateLimiter()
_answer_cache = AIP.TTLCache()


def _agent_read(question, read):
    """Read-only agent answer. Any logged-in user; nothing is written except the chat history line."""
    cur = mysql.connection.cursor()
    try:
        _ensure_chat_table(cur)
        if read['read'] == 'medicine_shelf':
            answer = AR.shelf_answer(AT.find_medicine(cur, read['text'], 10), read['text'])
        else:
            answer = AR.customer_answer(AT.find_customer(cur, read['text'], 8), read['text'])
        cur.execute("INSERT INTO chat_history (user_id, question, answer) VALUES (%s, %s, %s)",
                    (session['user_id'], question[:300], answer))
        mysql.connection.commit()
        return jsonify({'answer': answer, 'chips': DEFAULT_CHIPS})
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('agent read failed')
        return jsonify({'answer': 'Could not read the data. Please try again.', 'chips': DEFAULT_CHIPS})
    finally:
        cur.close()


def _agent_chat(question, parsed):
    """Chat side of a write command: returns a proposal + token. Nothing is changed here."""
    if 'error' in parsed:
        return jsonify({'answer': parsed['error'], 'chips': DEFAULT_CHIPS})
    if session.get('role') not in AGENT_ROLES:
        return jsonify({'answer': 'Only Admin or Pharmacist can change data.', 'chips': DEFAULT_CHIPS})
    cur = mysql.connection.cursor()
    try:
        AT.ensure_agent_table(cur)
        _ensure_chat_table(cur)
        params = dict(parsed['params'])
        if parsed['action'] == 'set_shelf_location':
            cur.execute("SELECT medicine_id, name FROM medicines WHERE is_deleted = 0 AND LOWER(name) = LOWER(%s)",
                        (parsed['medicine_name'],))
            rows = cur.fetchall()
            if not rows:
                raise AT.AgentError(f"Medicine '{parsed['medicine_name']}' was not found. Please check the name.")
            params['medicine_id'] = rows[0]['medicine_id']
        prop = AT.propose(cur, session['user_id'], parsed['action'], params, datetime.now())
        answer = f"{prop['summary']}. Press the confirm button (valid for 5 minutes)."
        cur.execute("INSERT INTO chat_history (user_id, question, answer) VALUES (%s, %s, %s)",
                    (session['user_id'], question[:300], answer))
        mysql.connection.commit()
        return jsonify({'answer': answer, 'chips': DEFAULT_CHIPS, 'token': prop['token']})
    except AT.AgentError as e:
        mysql.connection.rollback()
        return jsonify({'answer': str(e), 'chips': DEFAULT_CHIPS})
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('agent propose failed')
        return jsonify({'answer': 'The change could not be prepared. Nothing was changed.', 'chips': DEFAULT_CHIPS})
    finally:
        cur.close()


@app.route('/chatbot')
@login_required
@guarded
def chatbot():
    cur = mysql.connection.cursor()
    try:
        _ensure_chat_table(cur)
        cur.execute("""SELECT question, answer, created_at FROM chat_history
                       WHERE user_id = %s ORDER BY created_at DESC LIMIT 30""", (session['user_id'],))
        rows = cur.fetchall()
    finally:
        cur.close()
    history = list(reversed(rows))   # oldest first
    # v91.00: the header shows whether online AI (Gemini etc.) is connected
    try:
        from pharmacy.ai_client import ai_status
        ai_online, ai_provider = ai_status()
    except Exception:
        ai_online, ai_provider = False, ''
    return render_template('chatbot.html', history=history, chips=DEFAULT_CHIPS,
                           ai_online=ai_online, ai_provider=ai_provider)

@app.route('/chatbot/api', methods=['POST'])
@guarded
def chatbot_api():
    """Used by the chat page (no page reload)."""
    if 'user_id' not in session:
        return jsonify({'error': 'Session expired. Please login again.'}), 401
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return jsonify({'error': 'Please type a question.'}), 400
    if not _limiter.allow(session['user_id']):
        return jsonify({'error': 'Too many questions in a short time. Please wait a minute and try again.'}), 429
    parsed = AR.parse_write(question)            # v72: data changes go through the agent (propose, then Confirm)
    if parsed is not None:
        return _agent_chat(question, parsed)
    read = AR.parse_read(question)               # v74: read-only agent queries (shelf, phone lookup)
    if read is not None:
        return _agent_read(question, read)
    # Live-data questions (sales, stock, dues) are never cached - their answers change.
    live_words = ('sale', 'stock', 'dues', 'udhaar', 'today', 'aaj', 'kitna', 'kitne', 'expir')
    cache_key = (session['user_id'], question.lower())
    use_cache = not any(w in cache_key[1] for w in live_words)
    if use_cache:
        cached = _answer_cache.get(cache_key)
        if cached is not None:
            return jsonify({'answer': cached[0], 'chips': cached[1]})
    answer, chips = _chat_reply(question)
    if use_cache:
        _answer_cache.put(cache_key, (answer, chips))
    return jsonify({'answer': answer, 'chips': chips})

@app.route('/chatbot/ask', methods=['POST'])
@login_required
@guarded
def chatbot_ask():
    """Backup route if JavaScript is turned off."""
    question = request.form.get('question', '').strip()
    if question:
        _chat_reply(question)
    return redirect(url_for('chatbot'))

@app.route('/chatbot/clear', methods=['POST'])
@login_required
@guarded
def chatbot_clear():
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM chat_history WHERE user_id = %s", (session['user_id'],))
        mysql.connection.commit()
        cur.close()
        session.pop('chat_ctx', None)
        flash('Chat history cleared', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')
    return redirect(url_for('chatbot'))
