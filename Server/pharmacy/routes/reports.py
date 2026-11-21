"""Routes: reports."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.lib import _csv_response, _expiry_rows, _fill_days, _report_dates, _sales_figures, _stock_rows
from flask import make_response
from pharmacy.services import product_sections as PS


@app.route('/reports')
@login_required
@role_required('Admin')
@guarded
def reports():
    cur = mysql.connection.cursor()
    try:
        tab = request.args.get('tab', 'overview')
        if tab not in REPORT_TABS:
            tab = 'overview'
        start_date, end_date = _report_dates()
        today = date.today()
        fig = _sales_figures(cur, start_date, end_date)
        low = _stock_rows(cur) if tab == 'stock' else []
        exp = _expiry_rows(cur) if tab == 'expiry' else []
        sec_rows = _section_rows(cur, start_date, end_date) if tab == 'sections' else []
        slow_rows = _slow_rows(cur, start_date, end_date) if tab == 'slow' else []
        # Every day of the range gets a point (zero on days without sales), oldest first.
        chart = _fill_days(fig['daily'], start_date, end_date, 'sale_day')
        chart_days = [(d['sale_day'].strftime('%d %b') if hasattr(d['sale_day'], 'strftime') else str(d['sale_day'])) for d in chart]
        chart_revenue = [round(float(d['revenue']), 2) for d in chart]
        resp = make_response(render_template('reports.html', tab=tab,
                               start_date=start_date, end_date=end_date,
                               today=today.isoformat(), today_date=today,
                               week_ago=(today - timedelta(days=6)).isoformat(),
                               month_ago=(today - timedelta(days=29)).isoformat(),
                               year_ago=(today - timedelta(days=364)).isoformat(),
                               daily=fig['daily'], best=fig['best'], profit_rows=fig['profit_rows'],
                               total_revenue=fig['total_revenue'], total_invoices=fig['total_invoices'],
                               total_items=fig['total_items'], total_cost=fig['total_cost'],
                               total_profit=fig['total_profit'], margin_pct=fig['margin_pct'],
                               avg_invoice=fig['avg_invoice'], low=low, exp=exp,
                               sec_rows=sec_rows, slow_rows=slow_rows,
                               chart_days=chart_days, chart_revenue=chart_revenue))
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    except Exception as e:
        app.logger.exception('reports page failed')
        flash_unexpected('Could not load reports.')
        return redirect(url_for('dashboard'))
    finally:
        cur.close()

@app.route('/reports/export/<rtype>')
@login_required
@role_required('Admin')
@guarded
def export_report(rtype):
    """Download a report as CSV (default), Excel (fmt=xlsx) or PDF (fmt=pdf). Sprint 2 adds the tax summary."""
    if rtype not in ('sales', 'profit', 'stock', 'expiry', 'tax', 'purchases'):  # v88.00: E2 purchases export
        flash('Unknown report type', 'danger')
        return redirect(url_for('reports'))
    fmt = request.args.get('fmt', 'csv')
    if fmt not in ('csv', 'xlsx', 'pdf', 'docx'):
        fmt = 'csv'
    cur = mysql.connection.cursor()
    try:
        start_date, end_date = _report_dates()
        stamp = datetime.now().strftime('%Y%m%d_%H%M')
        period = f'{start_date} to {end_date}'
        notes = None
        summary = None
        if rtype == 'sales':
            fig = _sales_figures(cur, start_date, end_date)
            headers = ['Date', 'Invoices', 'Net revenue (Rs.)']
            rows = [(d['sale_day'], int(d['invoices']), round(float(d['revenue']), 2)) for d in fig['daily']]
            title, base = 'Sales report', f'sales_{start_date}_to_{end_date}'
            summary = [('Net revenue (Rs.)', round(fig['total_revenue'], 2)), ('Invoices', fig['total_invoices'])]
        elif rtype == 'profit':
            fig = _sales_figures(cur, start_date, end_date)
            headers = ['Medicine', 'Sold', 'Revenue (Rs.)', 'Cost (Rs.)', 'Profit (Rs.)', 'Margin %']
            rows = [(r['name'], r['sold'], round(r['revenue'], 2), round(r['cost'], 2),
                     round(r['profit'], 2), round(r['margin'], 1)) for r in fig['profit_rows']]
            title, base = 'Profit report', f'profit_{start_date}_to_{end_date}'
            summary = [('Profit (Rs.)', round(fig['total_profit'], 2)), ('Margin %', round(fig['margin_pct'], 1))]
        elif rtype == 'purchases':   # v88.00: E2 - purchase orders in the chosen date range
            cur.execute("""SELECT po.po_id, po.order_date, s.name AS supplier, po.status, po.total_amount
                           FROM purchase_orders po JOIN suppliers s ON s.supplier_id = po.supplier_id
                           WHERE po.order_date BETWEEN %s AND %s ORDER BY po.order_date, po.po_id""",
                        (start_date, end_date))
            prows = cur.fetchall()
            headers = ['Date', 'PO number', 'Supplier', 'Status', 'Total (Rs.)']
            rows = [(r['order_date'], r['po_id'], r['supplier'], r['status'], round(float(r['total_amount'] or 0), 2)) for r in prows]
            title, base = 'Purchases report', f'purchases_{start_date}_to_{end_date}'
            summary = [('Purchase orders', len(rows)), ('Total (Rs.)', round(sum(r[4] for r in rows), 2))]
        elif rtype == 'stock':
            headers = ['Medicine', 'Stock', 'Reorder level']
            rows = [(r['name'], r['stock_quantity'], r['reorder_level']) for r in _stock_rows(cur)]
            title, base = 'Low stock report', f'low_stock_{stamp}'
        elif rtype == 'expiry':
            headers = ['Medicine', 'Batch', 'Expiry date', 'Quantity']
            rows = [(r['name'], r['batch_number'], r['expiry_date'], r['quantity']) for r in _expiry_rows(cur)]
            title, base = 'Expiry report (next 90 days and expired)', f'expiry_{stamp}'
        else:   # tax summary: one line per day, for the accountant
            cur.execute("""SELECT DATE(sale_date) AS sale_day, COUNT(*) AS invoices,
                                  IFNULL(SUM(subtotal_amount), 0) AS subtotal, IFNULL(SUM(discount_amount), 0) AS discount,
                                  IFNULL(SUM(tax_amount), 0) AS tax, IFNULL(SUM(total_amount), 0) AS total,
                                  IFNULL(SUM(returned_amount), 0) AS returned
                           FROM sales WHERE DATE(sale_date) BETWEEN %s AND %s
                           GROUP BY DATE(sale_date) ORDER BY sale_day ASC""", (start_date, end_date))
            days = cur.fetchall()
            headers = ['Date', 'Invoices', 'Subtotal (Rs.)', 'Discount (Rs.)', 'Tax (Rs.)', 'Total (Rs.)', 'Returns (Rs.)']
            rows = [(d['sale_day'], int(d['invoices']), round(float(d['subtotal']), 2), round(float(d['discount']), 2),
                     round(float(d['tax']), 2), round(float(d['total']), 2), round(float(d['returned']), 2)) for d in days]
            tax_total = round(sum(float(d['tax']) for d in days), 2)
            returns_total = round(sum(float(d['returned']) for d in days), 2)
            summary = [('Tax collected (Rs.)', tax_total), ('Returns in period (Rs.)', returns_total),
                       ('Tax rate set in Settings (%)', get_tax_rate())]
            notes = ['Prepared from the sales records. Tax on returned sales is not reversed automatically.',
                     'Confirm the rate, the period and the filing rules with your tax advisor before filing.']
            title, base = 'Sales tax summary', f'tax_summary_{start_date}_to_{end_date}'

        subtitle = f'Period: {period}   |   Shop: {shop_name_for_reports()}'
        if fmt == 'csv':
            return _csv_response(headers, rows, base + '.csv')
        if fmt == 'xlsx':
            from pharmacy.exports import build_xlsx
            data = build_xlsx(title, headers, rows, summary=summary, notes=notes)
            return _file_response(data, base + '.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        if fmt == 'docx':
            from pharmacy.exports import build_docx
            data = build_docx(title, headers, rows, summary=summary, notes=notes, subtitle=subtitle)
            return _file_response(data, base + '.docx',
                                  'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        from pharmacy.exports import build_pdf
        data = build_pdf(title, headers, rows, summary=summary, notes=notes, subtitle=subtitle)
        return _file_response(data, base + '.pdf', 'application/pdf')
    except Exception as e:
        app.logger.exception('report export failed')
        flash_unexpected('Could not export report.')
        return redirect(url_for('reports'))
    finally:
        cur.close()


def _file_response(data, filename, mimetype):
    from flask import Response
    return Response(data, mimetype=mimetype,
                    headers={'Content-Disposition': f'attachment; filename="{filename}"',
                             'Cache-Control': 'no-store'})


def shop_name_for_reports():
    try:
        return get_all_settings()['shop_name'] or 'MediGen AI Pro'
    except Exception:
        app.logger.exception('could not read shop name for report, using default')
        return 'MediGen AI Pro'


def _section_rows(cur, start, end):
    """v86.16: sales, cost and profit per product section for the period (returns taken out)."""
    cur.execute("""SELECT m.dosage_form, si.quantity, si.unit_price,
                          IFNULL((SELECT SUM(ri.quantity) FROM sale_return_items ri
                                  WHERE ri.sale_item_id = si.sale_item_id), 0) AS returned_qty,
                          COALESCE(b.purchase_price, m.cost_price, 0) AS unit_cost
                   FROM sale_items si
                   JOIN sales s ON si.sale_id = s.sale_id
                   JOIN medicines m ON si.medicine_id = m.medicine_id
                   LEFT JOIN batches b ON si.batch_id = b.batch_id
                   WHERE DATE(s.sale_date) BETWEEN %s AND %s""", (start, end))
    agg = {k: {'key': k, 'label': PS.SECTION_LABEL[k], 'sold': 0, 'revenue': 0.0, 'cost': 0.0}
           for k in PS.SECTION_KEYS}
    for r in cur.fetchall():
        net = int(r['quantity']) - int(r['returned_qty'])
        if net <= 0:
            continue
        row = agg[PS.section_for(r['dosage_form'])]
        row['sold'] += net
        row['revenue'] += net * float(r['unit_price'] or 0)
        row['cost'] += net * float(r['unit_cost'] or 0)
    rows = list(agg.values())
    total_rev = sum(r['revenue'] for r in rows)
    for r in rows:
        r['profit'] = r['revenue'] - r['cost']
        r['share'] = (r['revenue'] / total_rev * 100) if total_rev else 0.0
    return rows


def _slow_rows(cur, start, end):
    """v86.16: medicines with stock on the shelf that did not sell at all in the period."""
    cur.execute("""SELECT m.name, m.dosage_form, m.stock_quantity, m.price
                   FROM medicines m
                   WHERE m.is_deleted = 0 AND m.stock_quantity > 0
                     AND m.medicine_id NOT IN (
                         SELECT si.medicine_id FROM sale_items si
                         JOIN sales s ON si.sale_id = s.sale_id
                         WHERE DATE(s.sale_date) BETWEEN %s AND %s)
                   ORDER BY m.stock_quantity DESC LIMIT 200""", (start, end))
    rows = []
    for r in cur.fetchall():
        rows.append({'name': r['name'], 'section': PS.SECTION_LABEL[PS.section_for(r['dosage_form'])],
                     'stock': int(r['stock_quantity']), 'value': round(int(r['stock_quantity']) * float(r['price'] or 0), 2)})
    return rows
