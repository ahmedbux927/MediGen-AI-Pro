"""Routes: dashboard."""
from pharmacy.services import drip_report as RPT
from pharmacy.services import product_sections as PS
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _fill_days
from flask import make_response
from datetime import datetime


# ---------- DASHBOARD ----------
@app.route('/dashboard')
@login_required
@guarded
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM medicines WHERE is_deleted = 0")
    total_meds = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM customers")
    total_cust = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM sales WHERE DATE(sale_date)=CURDATE()")
    today_sales = cur.fetchone()['c']
    cur.execute("SELECT IFNULL(SUM(total_amount - returned_amount),0) AS s FROM sales WHERE DATE(sale_date)=CURDATE()")
    today_revenue = cur.fetchone()['s']
    # v86.69: low stock for every section, with the section name on each row and a count per section
    cur.execute("""SELECT medicine_id, name, stock_quantity, reorder_level, dosage_form FROM medicines
                   WHERE is_deleted = 0 AND stock_quantity <= reorder_level ORDER BY name""")
    low_stock = cur.fetchall()
    _labels = {k: lab for k, lab, _ic, _d in PS.SECTIONS}
    low_by_section = [{'key': k, 'label': lab, 'count': 0} for k, lab, _ic, _d in PS.SECTIONS]
    for _r in low_stock:
        _k = PS.section_for(_r.get('dosage_form'))
        _r['section'] = _labels.get(_k, _k)
        for _s in low_by_section:
            if _s['key'] == _k:
                _s['count'] += 1
    # v86.70: expiring batches for every section, with the section name, earliest first
    cur.execute("""SELECT b.batch_id, m.name, b.batch_number, b.expiry_date, b.quantity, m.dosage_form
                   FROM batches b JOIN medicines m ON b.medicine_id = m.medicine_id
                   WHERE m.is_deleted = 0 AND b.expiry_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 90 DAY)
                   ORDER BY b.expiry_date, m.name""")
    expiring_all = cur.fetchall()
    _elabels = {k: lab for k, lab, _ic, _d in PS.SECTIONS}
    expiring_by_section = [{'key': k, 'label': lab, 'count': 0} for k, lab, _ic, _d in PS.SECTIONS]
    for _e in expiring_all:
        _k = PS.section_for(_e.get('dosage_form'))
        _e['section'] = _elabels.get(_k, _k)
        for _s in expiring_by_section:
            if _s['key'] == _k:
                _s['count'] += 1
    expiring_total = len(expiring_all)
    expiring = expiring_all[:5]
    # v52: pending purchase orders tile (read-only)
    cur.execute("SELECT COUNT(*) AS c FROM purchase_orders WHERE status = 'Pending'")
    pending_po = cur.fetchone()['c']
    # Last 7 days, today included. Days without sales are filled with zero so the bars line up.
    today = date.today()
    week_start = today - timedelta(days=6)
    cur.execute("""
        SELECT DATE(sale_date) AS day, COUNT(*) AS invoices,
               IFNULL(SUM(total_amount - returned_amount), 0) AS revenue
        FROM sales
        WHERE DATE(sale_date) BETWEEN %s AND %s
        GROUP BY DATE(sale_date)
        ORDER BY day ASC
    """, (week_start, today))
    chart_data = _fill_days(cur.fetchall(), week_start, today, 'day')
    chart_days = [row['day'].isoformat() for row in chart_data]
    chart_revenue = [row['revenue'] for row in chart_data]
    chart_invoices = [row['invoices'] for row in chart_data]
    chart_has_data = any(chart_invoices)

    # Top 5 by units sold, net of returns (same rule as the Reports page).
    cur.execute("""
        SELECT m.name,
               SUM(si.subtotal) AS revenue,
               SUM(si.quantity - IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                         WHERE ri.sale_item_id = si.sale_item_id), 0)) AS sold
        FROM sale_items si
        JOIN medicines m ON si.medicine_id = m.medicine_id
        GROUP BY m.name
        HAVING sold > 0
        ORDER BY sold DESC
        LIMIT 5
    """)
    top_meds = cur.fetchall()
    top_med_names = [row['name'] for row in top_meds]
    top_med_sold = [int(row['sold']) for row in top_meds]
    top_med_revenue = [float(row['revenue'] or 0) for row in top_meds]   # v52: gross value, same rule as the chatbot

    try:                                  # v85: drip and injection tile; never breaks the dashboard
        drip = RPT.summary(cur)
    except Exception:
        app.logger.exception('drip summary failed (dashboard still opens)')
        drip = None
    try:                                  # v86: all product sections on the dashboard
        sections = PS.overview(cur)
        section_rows = [{'key': k, 'label': lab, 'icon': ic, **sections[k]} for k, lab, ic, _d in PS.SECTIONS]
        total_meds = sections['medicines']['items']   # v86.67: this card is the Medicines section only; other sections are listed beside it
    except Exception:
        app.logger.exception('section overview failed (dashboard still opens)')
        section_rows = None
    rec = None
    try:                                  # v86.76: every record per product section (sales, stock, purchase, profit, customers)
        from pharmacy.services import dashboard_records as DR2
        rec = DR2.build(cur, date.today())
    except Exception:
        app.logger.exception('section records failed (dashboard still opens)')
    pl_rows, pl_totals = None, None
    try:                                  # v86.59: profit and loss for every section, today and this month
        from pharmacy.routes.reports import _section_rows as _pl_rows
        today_iso = date.today().isoformat()
        month_iso = date.today().replace(day=1).isoformat()
        day_rows = {r['key']: r for r in _pl_rows(cur, today_iso, today_iso)}
        mon_rows = {r['key']: r for r in _pl_rows(cur, month_iso, today_iso)}
        pl_rows = []
        for k, lab, ic, _d in PS.SECTIONS:
            d, m = day_rows.get(k, {}), mon_rows.get(k, {})
            pl_rows.append({'key': k, 'label': lab, 'icon': ic,
                            'd_sold': d.get('sold', 0), 'd_rev': d.get('revenue', 0.0), 'd_cost': d.get('cost', 0.0),
                            'd_profit': d.get('profit', 0.0),
                            'm_sold': m.get('sold', 0), 'm_rev': m.get('revenue', 0.0), 'm_profit': m.get('profit', 0.0)})
        pl_totals = {k2: sum(r[k2] for r in pl_rows) for k2 in ('d_rev', 'd_cost', 'd_profit', 'm_rev', 'm_profit')}
    except Exception:
        app.logger.exception('profit and loss by section failed (dashboard still opens)')
    money = {}                            # v86.61: cash in hand, total udhaar, expenses and net profit
    try:
        from pharmacy.repos import cash_drawer as CDR
        from pharmacy.repos import expenses as EXP
        from pharmacy.repos.business import customers_with_dues
        from pharmacy.services import cash_drawer as CDS
        sess = CDR.open_session(cur)
        if sess:
            since = sess['opened_at']
            money['cash_opening'] = float(sess['opening_amount'] or 0)
            money['cash_since'] = sess['opened_at']
            money['cash_in_hand'] = CDS.expected_cash(float(sess['opening_amount'] or 0),
                                                       CDR.cash_sales_since(cur, since),
                                                       CDR.cash_refunds_since(cur, since),
                                                       *CDR.movement_totals(cur, sess['session_id']))
        money['udhaar_total'] = round(sum(float(r['due'] or 0) for r in customers_with_dues(cur)), 2)
        m_start = date.today().replace(day=1).isoformat()
        t_iso = date.today().isoformat()
        money['exp_today'] = EXP.total_between(cur, t_iso, t_iso)
        money['exp_month'] = EXP.total_between(cur, m_start, t_iso)
        if pl_totals:
            money['net_today'] = pl_totals['d_profit'] - money['exp_today']
            money['net_month'] = pl_totals['m_profit'] - money['exp_month']
    except Exception:
        app.logger.exception('cash, udhaar and expense figures failed (dashboard still opens)')
    ai_summary = None                            # Stage 6: optional daily AI summary (off by default)
    try:
        if get_setting('ai_daily_summary') == '1':
            import json as _json
            from pharmacy.services import agent_tools as _AT
            from pharmacy.services import ai_pro as _AIP
            from pharmacy.ai_client import ask_ai as _ask_ai
            _today_iso = date.today().isoformat()
            _cached = _json.loads(get_setting('ai_summary_cache') or '{}')
            if _cached.get('date') == _today_iso and _cached.get('text'):
                ai_summary = _cached['text']
            else:
                _agg = {'sales_today': today_revenue, 'bills_today': today_sales,
                        'low_stock': len(_AT.low_stock(cur)),
                        'expiring_30d': len(_AT.expiring(cur, date.today(), 30)),
                        'dues_total': money.get('udhaar_total', 0)}
                _text, _why = _ask_ai(_AIP.build_summary_prompt(_agg))
                if _text:
                    ai_summary = _text.strip()
                    cur.execute("""INSERT INTO app_settings (setting_key, setting_value) VALUES ('ai_summary_cache', %s)
                                   ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)""",
                                (_json.dumps({'date': _today_iso, 'text': ai_summary}),))
                    mysql.connection.commit()
    except Exception:
        app.logger.exception('daily AI summary failed (dashboard still opens)')
    cur.close()
    _h = datetime.now().hour                         # first value only; dashboard.js updates it by the clock
    greet = 'Good morning' if _h < 12 else ('Good afternoon' if _h < 17 else 'Good evening')
    resp = make_response(render_template('dashboard.html', greet=greet, drip=drip, section_rows=section_rows,
                           pl_rows=pl_rows, pl_totals=pl_totals, money=money, ai_summary=ai_summary,
                           total_meds=total_meds,
                           total_cust=total_cust,
                           today_sales=today_sales,
                           today_revenue=today_revenue,
                           low_stock=low_stock, low_by_section=low_by_section,
                           expiring=expiring, expiring_total=expiring_total, expiring_by_section=expiring_by_section,
                           chart_days=chart_days,
                           chart_revenue=chart_revenue,
                           chart_invoices=chart_invoices,
                           chart_has_data=chart_has_data,
                           top_med_names=top_med_names,
                           top_med_sold=top_med_sold,
                           sales_rows=list(zip(chart_days, chart_invoices, chart_revenue)),
                           med_rows=list(zip(top_med_names, top_med_sold)),
                           pending_po=pending_po,
                           rec=rec,
                           top_med_revenue=top_med_revenue))
    # Always fetch fresh numbers: a Back button must not show a chart from before the last sale.
    resp.headers['Cache-Control'] = 'no-store'
    return resp
