"""Shared helpers: settings, audit log, prescriptions, reports, users, chat, backup helpers."""
import os
import re
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.ai_client import ai_enabled, ask_ai, ensure_pharmacist_note, friendly_reason  # v88.00: pharmacist note
from chatbot_engine import NOT_UNDERSTOOD


# ---------- MEDICINES ----------
MEDICINE_FORMS = ['Tablet', 'Capsule', 'Powder', 'Sachet', 'Suppository', 'Inhaler', 'Other',
                  'Syrup', 'Suspension', 'Oral liquid', 'Drops', 'Oral rinse', 'Oral solution',
                  'Cream', 'Gel', 'Ointment', 'Lotion', 'Topical cream/gel/ointment',
                  'Injection', 'Drip / IV fluid',
                  'Bandage', 'Dressing', 'Syringe', 'Gauze / cotton', 'Plaster', 'Other product']
ADJUST_REASONS = {
    'out': ['Damaged', 'Expired', 'Lost / Theft', 'Returned to supplier', 'Correction'],
    'in':  ['Found', 'Customer return', 'Correction'],
}

def _like(text):
    """Make user text safe for a LIKE search."""
    text = text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return '%' + text + '%'

def _read_medicine_form(d):
    """Read and check the add/edit form. Returns (data, error)."""
    name = d.get('name', '').strip()
    if not name:
        return None, 'Medicine name is required'
    try:
        price = float(d['price'])
        cost = float(d.get('cost_price') or 0)
        reorder = int(d.get('reorder') or 20)
    except (ValueError, KeyError):
        return None, 'Invalid number format'
    if not (math.isfinite(price) and math.isfinite(cost)) or price < 0 or cost < 0 or reorder < 0:
        return None, 'Price, cost and reorder level cannot be negative'
    if not d.get('category_id'):
        return None, 'Please choose a category'
    barcode = (d.get('barcode') or '').strip()
    if barcode and not re.fullmatch(r'[A-Za-z0-9\-]{4,64}', barcode):
        return None, 'Barcode must be 4 to 64 letters or digits (no spaces)'
    dform = (d.get('dosage_form') or '').strip()
    if dform and dform not in MEDICINE_FORMS:
        return None, 'Please choose a valid dosage form'
    shelf = (d.get('rack_location') or '').strip()
    if len(shelf) > 40:
        return None, 'Shelf location can be at most 40 characters'
    return {'name': name, 'category_id': d['category_id'], 'barcode': barcode or None,
            'price': price, 'cost': cost, 'reorder': reorder, 'rack_location': shelf or None, 'dosage_form': dform or None}, None

# ---------- BATCHES / EXPIRY TRACKER ----------
BATCH_STATUS_SQL = """CASE WHEN b.quantity <= 0 THEN 'empty'
                           WHEN b.expiry_date < CURDATE() THEN 'expired'
                           WHEN b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY) THEN 'soon'
                           ELSE 'ok' END"""

def _stock_mismatches(cur):
    cur.execute("""SELECT m.medicine_id, m.name, IFNULL(m.stock_quantity, 0) AS stock, IFNULL(m.cost_price, 0) AS cost,
                          IFNULL(SUM(b.quantity), 0) AS batch_qty
                   FROM medicines m LEFT JOIN batches b ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0
                   GROUP BY m.medicine_id, m.name, m.stock_quantity, m.cost_price
                   HAVING IFNULL(m.stock_quantity, 0) <> IFNULL(SUM(b.quantity), 0)
                   ORDER BY m.name""")
    out = []
    for r in cur.fetchall():
        r['stock'], r['batch_qty'] = int(r['stock']), int(r['batch_qty'])
        r['diff'] = r['stock'] - r['batch_qty']        # + = batches are missing units, - = batches have too many
        out.append(r)
    return out
# ---------- SALES ----------
PAY_METHODS = ('Cash', 'Card', 'Online', 'JazzCash', 'Easypaisa')  # v94: mobile wallets
DUE_SQL = "(s.total_amount - s.returned_amount - s.paid_amount)"

def _valid_date(text):
    try:
        return datetime.strptime(text, '%Y-%m-%d').date().isoformat()
    except (ValueError, TypeError):
        return ''

def _num(text, default=0.0):
    text = (text or '').strip()
    if not text:
        return default
    value = float(text)
    if not math.isfinite(value):
        raise ValueError('Please enter a valid number')
    return value

def _return_items(cur, sale_id, ratio):
    cur.execute("""SELECT si.sale_item_id, si.medicine_id, si.batch_id, si.quantity, si.unit_price, m.name,
                          IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                  WHERE ri.sale_item_id = si.sale_item_id), 0) AS returned_qty
                   FROM sale_items si JOIN medicines m ON si.medicine_id = m.medicine_id
                   WHERE si.sale_id = %s ORDER BY si.sale_item_id""", (sale_id,))
    items = cur.fetchall()
    for it in items:
        it['returned_qty'] = int(it['returned_qty'])
        it['returnable'] = int(it['quantity']) - it['returned_qty']
        it['unit_refund'] = round(float(it['unit_price'] or 0) * ratio, 4)
    return items

# ---------- PURCHASE ----------
def _as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return datetime.strptime(str(v)[:10], '%Y-%m-%d').date()

class BatchConflict(Exception):
    """Same batch number already exists with a different expiry date."""

def _read_purchase_rows(form, today):
    """Read the item rows of the purchase form. Returns (rows, error_message)."""
    med_ids = form.getlist('medicine_id[]')
    qtys = form.getlist('quantity[]')
    prices = form.getlist('unit_price[]')
    batch_nos = form.getlist('batch_number[]')
    expiries = form.getlist('expiry_date[]')

    def at(lst, i):
        return (lst[i] if i < len(lst) else '').strip()

    rows = []
    for i, mid in enumerate(med_ids):
        n = i + 1
        qty_s, price_s, exp_s = at(qtys, i), at(prices, i), at(expiries, i)
        if not mid and not qty_s:
            continue                                   # empty row, skip it
        if not mid:
            return None, f'Row {n}: please choose a medicine'
        try:
            medicine_id, qty, price = int(mid), int(qty_s), float(price_s)
        except ValueError:
            return None, f'Row {n}: quantity and price must be numbers'
        if qty <= 0:
            return None, f'Row {n}: quantity must be more than 0'
        if price < 0 or not math.isfinite(price):
            return None, f'Row {n}: price must be a valid amount'
        if qty > 1000000 or price > 1000000:
            return None, f'Row {n}: quantity or price is too large'
        try:
            expiry = datetime.strptime(exp_s, '%Y-%m-%d').date()
        except ValueError:
            return None, f'Row {n}: please enter the expiry date'
        if expiry <= today:
            return None, f'Row {n}: expiry date must be in the future'
        rows.append({'mid': medicine_id, 'qty': qty, 'price': price,
                     'batch': at(batch_nos, i)[:50], 'expiry': expiry})
    if not rows:
        return None, 'Please add at least one medicine'
    return rows, None

# ---------- SETTINGS (shop info, tax, discount limit) ----------
SETTING_DEFAULTS = {
    'shop_name': 'MEDIGEN',
    'shop_address': '',
    'shop_phone': '',
    'receipt_footer': 'Thank you for your purchase!',
    'tax_rate': str(Config.TAX_RATE),
    'cashier_max_discount': str(Config.CASHIER_MAX_DISCOUNT_PCT),
    # v91.00: online AI keys (Settings page). Values are secrets - never render them.
    'gemini_api_key': '',
}

def get_all_settings():
    """All settings, with defaults for anything not saved yet. Never raises."""
    values = dict(SETTING_DEFAULTS)
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT setting_key, setting_value FROM app_settings")
        for row in cur.fetchall():
            if row['setting_value'] is not None:
                values[row['setting_key']] = row['setting_value']
    except Exception:
        app.logger.exception('could not read settings, using defaults')
    finally:
        if cur:
            cur.close()
    return values

def backup_status():
    """v96: haalat of the backups folder — newest file, count, and whether it is stale (>48h)."""
    import glob as _glob
    from datetime import datetime as _dt
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    _files = sorted(_glob.glob(os.path.join(_root, 'backups', 'medigen_*.sql')), key=os.path.getmtime)
    if not _files:
        return {'exists': False, 'stale': True, 'count': 0}
    _last = _files[-1]
    _age_h = (_dt.now() - _dt.fromtimestamp(os.path.getmtime(_last))).total_seconds() / 3600
    return {'exists': True, 'stale': _age_h > 48, 'count': len(_files),
            'name': os.path.basename(_last), 'size_kb': max(1, round(os.path.getsize(_last) / 1024)),
            'when': _dt.fromtimestamp(os.path.getmtime(_last)).strftime('%d %b %Y, %I:%M %p'),
            'age_h': int(_age_h)}


def get_setting(key):
    return get_all_settings().get(key, SETTING_DEFAULTS.get(key, ''))

def get_tax_rate():
    try:
        return float(get_setting('tax_rate'))
    except (TypeError, ValueError):
        return float(Config.TAX_RATE)

def get_cashier_max():
    try:
        return float(get_setting('cashier_max_discount'))
    except (TypeError, ValueError):
        return float(Config.CASHIER_MAX_DISCOUNT_PCT)

@app.context_processor
def inject_shop():
    """Every page can show the shop name and receipt footer as {{ shop.name }}."""
    s = get_all_settings()
    return {'shop': {'name': s['shop_name'], 'address': s['shop_address'], 'phone': s['shop_phone'],
                     'footer': s['receipt_footer']}, 'db_down': bool(getattr(g, 'db_down', False))}

def _vendor_asset(local_rel, cdn_url):
    """Use the file in static/vendor/ when scripts/fetch_assets.py has saved it (works offline),
    otherwise the pinned CDN link (needs internet)."""
    path = os.path.join(app.static_folder, 'vendor', *local_rel.split('/'))
    if os.path.isfile(path):
        return url_for('static', filename='vendor/' + local_rel)
    return cdn_url

app.add_template_global(_vendor_asset, 'vendor_asset')

# ---------- AUDIT LOG ----------
def _audit_json(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)[:60000]

def _request_context():
    """Who/what made the request: request id, path, method, browser, IP."""
    try:
        return (getattr(g, 'request_id', None), request.path[:200], request.method[:8],
                (request.headers.get('User-Agent') or '')[:255], (request.remote_addr or '')[:45])
    except RuntimeError:          # outside a web request (e.g. a script)
        return (None, None, None, None, None)

_AUDIT_INSERT = """INSERT INTO audit_log (user_id, username, action, entity, entity_id, details, ip,
                   request_id, request_path, http_method, user_agent, status, old_values, new_values)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

def audit(cur, action, entity=None, entity_id=None, details='', before=None, after=None, status='ok'):
    """Add one audit row inside the caller's transaction (saved with its commit)."""
    rid, path, method, ua, ip = _request_context()
    try:
        cur.execute(_AUDIT_INSERT, (session.get('user_id'), session.get('user_name'), action, entity, entity_id,
                                    (details or '')[:500], ip, rid, path, method, ua, status,
                                    _audit_json(before), _audit_json(after)))
    except Exception:
        app.logger.exception('audit write failed')

def audit_direct(action, details='', user_id=None, username=None, status='ok', entity=None, entity_id=None,
                 before=None, after=None):
    """For events outside a transaction: logins, denied attempts, CSRF failures, restores."""
    rid, path, method, ua, ip = _request_context()
    cur = mysql.connection.cursor()
    try:
        cur.execute(_AUDIT_INSERT, (user_id, username, action, entity, entity_id, (details or '')[:500], ip,
                                    rid, path, method, ua, status, _audit_json(before), _audit_json(after)))
        mysql.connection.commit()
    except Exception:
        mysql.connection.rollback()
        app.logger.exception('audit write failed')
    finally:
        cur.close()

# ---------- PRESCRIPTIONS ----------
def _clean_doctor(name):
    """'Dr. Ahmed' / 'dr.ahmed' / 'Ahmed' -> 'Ahmed'  (Drake stays 'Drake')."""
    return re.sub(r'^(?:dr|doctor)\b\.?\s*', '', (name or '').strip(), flags=re.I).strip()

def doctor_label(name):
    n = _clean_doctor(name)
    return f"Dr. {n}" if n else "Dr. -"

app.add_template_global(doctor_label)

# Basic keyword check (NOT a medical system): (words in patient history, medicine words to warn about)
ALLERGY_RULES = [
    (('penicillin', 'amoxicillin', 'augmentin'), ('amoxicillin', 'augmentin', 'amoxiclav', 'penicillin')),
    (('aspirin',), ('aspirin', 'disprin')),
    (('asthma', 'ulcer', 'gastric', 'kidney', 'renal'), ('ibuprofen', 'brufen', 'naproxen', 'diclofenac', 'aspirin', 'disprin')),
    (('sulfa', 'sulpha'), ('cotrimoxazole', 'bactrim', 'sulfa')),
]

def allergy_warnings(history, med_names):
    """Return warning texts. They never block a sale: the pharmacist decides."""
    text = (history or '').lower()
    if not text.strip() or not med_names:
        return []
    out = []
    for name in med_names:
        first = (name.split() or [''])[0].lower()
        if len(first) >= 4 and first in text:
            out.append(f"Patient history mentions {first.title()}. Please check with the doctor before giving {name}.")
    for triggers, words in ALLERGY_RULES:
        hit = next((t for t in triggers if t in text), None)
        if not hit:
            continue
        for name in med_names:
            if any(w in name.lower() for w in words):
                out.append(f"Patient history mentions '{hit}'. {name} may not be suitable. Please check with the doctor or pharmacist.")
    unique = []
    for w in out:
        if w not in unique:
            unique.append(w)
    return unique

def _customer_or_error(cur, customer_id):
    customer_id = (customer_id or '').strip()
    if not customer_id.isdigit():
        raise ValueError('Please choose a customer')
    cur.execute("SELECT customer_id, medical_history FROM customers WHERE customer_id=%s", (customer_id,))
    cust = cur.fetchone()
    if not cust:
        raise ValueError('Customer not found')
    return cust

def _read_prescription_form(cur, form):
    """Check doctor, notes and medicine rows. Returns (doctor, notes, items, names)."""
    doctor = _clean_doctor(form.get('doctor_name', ''))[:100]
    if not doctor:
        raise ValueError('Please enter the doctor name')
    notes = form.get('notes', '').strip()[:1000] or None
    items, names = [], []
    rows = zip(form.getlist('medicine_id[]'), form.getlist('dosage[]'), form.getlist('duration[]'))
    for n, (mid, dose, dur) in enumerate(rows, 1):
        mid, dose, dur = (mid or '').strip(), (dose or '').strip(), (dur or '').strip()
        if not mid and not dose:
            continue                                   # empty row
        if not mid or not mid.isdigit():
            raise ValueError(f'Row {n}: please choose a medicine')
        if not dose:
            raise ValueError(f'Row {n}: please enter the dosage')
        if len(dose) > 100:
            raise ValueError(f'Row {n}: dosage text is too long')
        try:
            days = int(dur or 1)
        except ValueError:
            raise ValueError(f'Row {n}: duration must be a number of days')
        if not 1 <= days <= 365:
            raise ValueError(f'Row {n}: duration must be between 1 and 365 days')
        cur.execute("SELECT name FROM medicines WHERE medicine_id=%s", (mid,))
        med = cur.fetchone()
        if not med:
            raise ValueError(f'Row {n}: medicine not found')
        items.append((int(mid), dose, days))
        names.append(med['name'])
    if not items:
        raise ValueError('Please add at least one medicine')
    return doctor, notes, items, names

def _save_items(cur, pid, items):
    for mid, dose, days in items:
        cur.execute("""INSERT INTO prescription_items (prescription_id, medicine_id, dosage, duration_days)
                       VALUES (%s,%s,%s,%s)""", (pid, mid, dose, days))

# ---------- AUDIT LOG PAGE (developer view) ----------
REPORT_TABS = ('overview', 'sales', 'profit', 'stock', 'expiry', 'sections', 'slow')

def _report_dates():
    """Read start/end dates from the URL. Bad or missing dates fall back to the last 30 days."""
    today = date.today()
    start = _valid_date(request.args.get('start_date', '')) or (today - timedelta(days=29)).isoformat()
    end = _valid_date(request.args.get('end_date', '')) or today.isoformat()
    if start > end:
        start, end = end, start
    return start, end

def _as_day(value):
    """Turn a date, datetime or 'YYYY-MM-DD' text into a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()

def _fill_days(rows, start, end, key):
    """One row per calendar day from start to end (both included), oldest first.
    Days with no sales get zero invoices and zero revenue, so the charts show a real gap
    instead of skipping the day. `key` is the column that holds the day in `rows`."""
    by_day = {_as_day(r[key]): r for r in rows}
    out = []
    day = _as_day(start)
    last = _as_day(end)
    while day <= last:
        r = by_day.get(day)
        out.append({key: day,
                    'invoices': int(r['invoices']) if r else 0,
                    'revenue': round(float(r['revenue']), 2) if r else 0.0})
        day += timedelta(days=1)
    return out

def _sales_figures(cur, start, end):
    """Totals, per-medicine profit and daily sales for the period.
    Profit = net revenue (after returns) - cost of the units still sold (after returns).
    Known simplification: tax collected is counted as profit (tax is 0 unless TAX_RATE is set)."""
    cur.execute("""SELECT DATE(sale_date) AS sale_day, COUNT(*) AS invoices,
                          IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
                   FROM sales WHERE DATE(sale_date) BETWEEN %s AND %s
                   GROUP BY DATE(sale_date) ORDER BY sale_day DESC""", (start, end))
    daily = cur.fetchall()
    total_revenue = sum(float(d['revenue']) for d in daily)
    total_invoices = sum(int(d['invoices']) for d in daily)

    cur.execute("""SELECT m.name, si.quantity, si.unit_price,
                          IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                  WHERE ri.sale_item_id = si.sale_item_id), 0) AS returned_qty,
                          COALESCE(b.purchase_price, m.cost_price, 0) AS unit_cost
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   JOIN medicines m ON si.medicine_id = m.medicine_id
                   LEFT JOIN batches b ON si.batch_id = b.batch_id
                   WHERE DATE(s.sale_date) BETWEEN %s AND %s""", (start, end))
    per = {}
    for r in cur.fetchall():
        net = int(r['quantity']) - int(r['returned_qty'])
        if net <= 0:
            continue
        row = per.setdefault(r['name'], {'name': r['name'], 'sold': 0, 'revenue': 0.0, 'cost': 0.0})
        row['sold'] += net
        row['revenue'] += net * float(r['unit_price'] or 0)
        row['cost'] += net * float(r['unit_cost'] or 0)
    rows = []
    for row in per.values():
        row['profit'] = row['revenue'] - row['cost']
        row['margin'] = (row['profit'] / row['revenue'] * 100) if row['revenue'] else 0.0
        rows.append(row)
    total_cost = sum(r['cost'] for r in rows)
    total_items = sum(r['sold'] for r in rows)
    total_profit = total_revenue - total_cost
    return {
        'daily': daily,
        'total_revenue': total_revenue,
        'total_invoices': total_invoices,
        'total_items': total_items,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'margin_pct': (total_profit / total_revenue * 100) if total_revenue else 0.0,
        'avg_invoice': (total_revenue / total_invoices) if total_invoices else 0.0,
        'profit_rows': sorted(rows, key=lambda r: r['revenue'], reverse=True),
        'best': sorted(rows, key=lambda r: r['sold'], reverse=True)[:5],
    }

def _stock_rows(cur):
    cur.execute("""SELECT name, stock_quantity, reorder_level FROM medicines
                   WHERE stock_quantity <= reorder_level AND is_deleted = 0 ORDER BY stock_quantity ASC, name ASC""")
    return cur.fetchall()

def _expiry_rows(cur):
    """Batches with stock that expire within 90 days (expired ones included, so they are not missed)."""
    cur.execute("""SELECT m.name, b.batch_number, b.expiry_date, b.quantity
                   FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0 AND b.quantity > 0 AND b.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)
                   ORDER BY b.expiry_date ASC LIMIT 300""")
    return cur.fetchall()

def _csv_response(header, rows, filename):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    data = '\ufeff' + buf.getvalue()          # BOM so Excel shows Urdu/English correctly
    return Response(data, mimetype='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})

# ---------- AI CHATBOT (MediGen AI) ----------
_chat_table_ready = False

def _ensure_chat_table(cur):
    """Create chat_history table once, if it does not exist."""
    global _chat_table_ready
    if _chat_table_ready:
        return
    cur.execute("""CREATE TABLE IF NOT EXISTS chat_history (
                       chat_id INT AUTO_INCREMENT PRIMARY KEY,
                       user_id INT NOT NULL,
                       question TEXT,
                       answer TEXT,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    mysql.connection.commit()
    _chat_table_ready = True

def _chat_reply(question):
    """Ask the chatbot engine, save the chat, return (answer, chips)."""
    user = {'name': session.get('user_name'), 'role': session.get('role')}
    ctx = session.get('chat_ctx', {})
    cur = mysql.connection.cursor()
    try:
        _ensure_chat_table(cur)
        try:
            answer, chips = get_answer(cur, question, user, ctx)
        except Exception:
            app.logger.exception('Chatbot error')
            answer, chips = ('Sorry, I had a problem reading the data. Please try again.', DEFAULT_CHIPS)
        if answer.startswith(NOT_UNDERSTOOD) and ai_enabled():
            ai_text, _why = ask_ai(question)           # only for questions the offline engine cannot read
            if ai_text:
                answer = ensure_pharmacist_note(ai_text)   # v88.00: every AI answer carries the pharmacist-check note
                chips = DEFAULT_CHIPS
            else:
                # v92.00: say WHY the online AI stayed silent, so a saved-but-bad
                # key is not mistaken for "the key does nothing".
                answer += ('\n\n_Online AI is set up but did not answer: ' + friendly_reason(_why) +
                           '. Offline answers still work. Check the key in Settings, AI Assistant tab, with Test connection._')
        session['chat_ctx'] = ctx
        cur.execute("INSERT INTO chat_history (user_id, question, answer) VALUES (%s, %s, %s)",
                    (session['user_id'], question[:300], answer))
        mysql.connection.commit()
    finally:
        cur.close()
    return answer, chips

# MySQL error numbers that mean "the database cannot be reached" (server stopped, network cut, connection lost)
DB_DOWN_CODES = (2002, 2003, 2006, 2013)

def is_db_down(exc):
    """True when the error means the MySQL server cannot be reached right now (v86.52)."""
    try:
        code = exc.args[0] if getattr(exc, 'args', None) else None
    except Exception:
        return False
    return isinstance(code, int) and code in DB_DOWN_CODES and type(exc).__name__ in ('OperationalError', 'InterfaceError')


def guarded(view):
    """Safety net for one route: any unexpected error is logged in full, the database
    transaction is rolled back, and the user gets a short friendly message instead of a crash.
    HTTP errors (404, 401, redirects) pass through unchanged."""
    import functools
    from flask import request, redirect, url_for, jsonify, flash, render_template
    from urllib.parse import urlparse
    from werkzeug.exceptions import HTTPException

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as exc:
            import uuid
            code = 'ERR-' + uuid.uuid4().hex[:6].upper()     # v86.14: the same ID is shown to the user and written in the log
            app.logger.exception('Error %s: route %s (%s) failed', code, request.path, request.method)
            try:
                mysql.connection.rollback()     # never leave half-finished changes open
            except Exception as rb_exc:
                app.logger.warning('rollback after %s failed (%s)', code, type(rb_exc).__name__)
            if is_db_down(exc):                  # v86.52: clear message when MySQL is not running
                db_msg = ('Could not connect to the database. Check that MySQL is running, then try again. '
                          'No changes were saved.')
                if request.path.startswith(('/api/', '/chatbot/api')) or request.is_json:
                    return jsonify(error=db_msg, code='DB-DOWN'), 503
                if request.method == 'POST':
                    flash(db_msg + f' (ID {code})', 'danger')
                    ref = request.referrer or ''
                    if ref and urlparse(ref).netloc == request.host:
                        return redirect(ref)
                    return redirect(url_for('dashboard'))
                try:
                    return render_template('500.html', detail=db_msg + f' (ID {code})'), 503
                except Exception:
                    return f"<h2>Database is unavailable</h2><p>{db_msg}</p><p>ID: {code}</p>", 503
            if request.path.startswith(('/api/', '/chatbot/api')) or request.is_json:
                return jsonify(error=f'Something went wrong on the server. Error ID {code}.', code=code), 500
            if request.method == 'POST':
                flash(f'Something went wrong and the change may not have been saved. Error ID: {code}. '
                      'Check the log with this ID before trying again.', 'danger')
                ref = request.referrer or ''
                # only go back to a page on this same site (no redirect to other websites)
                if ref and urlparse(ref).netloc == request.host:
                    return redirect(ref)
                return redirect(url_for('dashboard'))
            try:
                return render_template('500.html', detail=f'Error ID: {code}  (page {request.path})'), 500
            except Exception:
                return f"<h2>500 - Server error</h2><p>Error ID: {code}</p><p><a href='/dashboard'>Back to Dashboard</a></p>", 500

    return wrapper

# Error codes shown to the user ("Error E-102") so the Admin can find the matching lines in the log.
ERROR_CODES = {
    'medicine_add': 'E-102',
    'medicine_edit': 'E-103',
    'sale_save': 'E-201',
    'user_add': 'E-302',
    'user_delete': 'E-301',
    'password_reset': 'E-401',
    'reset_code': 'E-402',
    'api_checkout': 'E-501',
    'agent': 'E-601',
}

def flash_unexpected(message, code=None):
    """Show a short, safe message to the user. The real error text goes only to the server log, with the code."""
    import uuid
    eid = code or ('ERR-' + uuid.uuid4().hex[:6].upper())      # v86.14: one ID per error, shown and logged
    app.logger.exception('Unexpected error [%s]: %s', eid, message)
    if code:                                                    # fixed codes (E-102 ...) keep their wording
        flash(f"{message} Error {code}. Please try again. If it keeps happening, check the log.", 'danger')
    else:
        flash(f"{message} Error ID: {eid}. Please try again. If it keeps happening, check the log with this ID.", 'danger')

def audit_as(cur, user_id, username, action, entity=None, entity_id=None, details='', before=None, after=None,
             status='ok'):
    """Audit row for API calls, which have no browser session. Saved with the caller's commit."""
    rid, path, method, ua, ip = _request_context()
    try:
        cur.execute(_AUDIT_INSERT, (user_id, username, action, entity, entity_id, (details or '')[:500], ip,
                                    rid, path, method, ua, status, _audit_json(before), _audit_json(after)))
    except Exception:
        app.logger.exception('audit write failed')

PROFILE_FIELDS = ['full_name', 'gender', 'email', 'phone', 'birthday', 'language', 'home_address',
                  'work_address', 'other_address', 'about', 'position', 'projects', 'license_info',
                  'experience', 'recommendations', 'volunteer', 'honors', 'awards', 'causes', 'services']
PROFILE_LONG = {'about', 'projects', 'experience', 'recommendations', 'volunteer', 'honors', 'awards', 'causes', 'services'}

# ---------- ERROR HANDLERS ----------
def _error_page(template, code, title):
    try:
        return render_template(template), code
    except Exception:
        return (f"<h2>{code} - {title}</h2><p><a href='/dashboard'>Back to Dashboard</a></p>"), code

def get_about_info():
    """System facts for the About tab. Never raises: missing parts show as 'unknown'."""
    import sys, platform
    info = {'version': APP_VERSION, 'released': APP_RELEASE_DATE, 'python': platform.python_version(),
            'os': platform.system() + ' ' + platform.release(), 'db_name': Config.MYSQL_DB,
            'db_version': 'unknown', 'counts': {}, 'audit_protected': False}
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT VERSION() AS v")
        info['db_version'] = cur.fetchone()['v']
        for label, table in [('Medicines', 'medicines'), ('Sales', 'sales'), ('Customers', 'customers'),
                             ('Prescriptions', 'prescriptions'), ('Users', 'users'), ('Audit entries', 'audit_log')]:
            cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
            info['counts'][label] = cur.fetchone()['n']
        cur.execute("SELECT COUNT(*) AS n FROM information_schema.triggers WHERE trigger_schema = DATABASE() AND trigger_name = 'trg_audit_no_update'")
        info['audit_protected'] = cur.fetchone()['n'] > 0
    except Exception:
        app.logger.exception('about info: database part failed')
    finally:
        if cur:
            cur.close()
    return info
