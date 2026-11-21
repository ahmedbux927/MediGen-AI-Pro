"""Routes: records."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403


# ---------- RECORDS CLEAR ----------
@app.route('/records-clear')
@login_required
@role_required('Admin')
@guarded
def records_clear():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) AS c FROM sales")
    total_sales = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM purchase_orders")
    total_purchases = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM prescriptions")
    total_prescriptions = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM customers")
    total_customers = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM suppliers")
    total_suppliers = cur.fetchone()['c']

    cur.close()
    return render_template('records_clear.html',
                          total_sales=total_sales,
                          total_purchases=total_purchases,
                          total_prescriptions=total_prescriptions,
                          total_customers=total_customers,
                          total_suppliers=total_suppliers)

@app.route('/records/clear/<string:table_name>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def clear_records(table_name):
    try:
        cur = mysql.connection.cursor()

        # extra safety: the Admin must type his own password
        cur.execute("SELECT password_hash FROM users WHERE user_id=%s", (session['user_id'],))
        me = cur.fetchone()
        typed = request.form.get('admin_password', '')
        if not me or not typed or not bcrypt.checkpw(typed.encode('utf-8'), me['password_hash'].encode('utf-8')):
            cur.close()
            flash('Wrong password. Nothing was deleted.', 'danger')
            return redirect(url_for('records_clear'))

        if table_name == 'sales':
            cur.execute("DELETE FROM sale_items")
            cur.execute("DELETE FROM sales")
            flash('All sales records have been deleted!', 'success')
        elif table_name == 'purchase_orders':
            cur.execute("DELETE FROM purchase_items")
            cur.execute("DELETE FROM purchase_orders")
            flash('All purchase records have been deleted!', 'success')
        elif table_name == 'prescriptions':
            cur.execute("DELETE FROM prescription_items")
            cur.execute("DELETE FROM prescriptions")
            flash('All prescriptions have been deleted!', 'success')
        elif table_name == 'customers':
            cur.execute("DELETE FROM customers")
            flash('All customers have been deleted!', 'success')
        elif table_name == 'suppliers':
            cur.execute("DELETE FROM suppliers")
            flash('All suppliers have been deleted!', 'success')
        else:
            flash('Invalid table name', 'danger')
            cur.close()
            return redirect(url_for('dashboard'))

        audit(cur, 'records.clear', table_name, None, f"all {table_name} deleted")
        mysql.connection.commit()
        cur.close()

    except Exception as e:
        mysql.connection.rollback()
        flash_unexpected('Something went wrong.')

    return redirect(url_for('dashboard'))
