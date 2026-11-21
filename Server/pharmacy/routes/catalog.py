"""Routes: categories, customers, suppliers. SQL lives in pharmacy/repos/catalog.py."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.repos import catalog as repo


# ---------- MANAGE CATEGORIES ----------
@app.route('/manage/categories')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def manage_categories():
    cur = mysql.connection.cursor()
    categories = repo.list_categories(cur)
    cur.close()
    return render_template('manage_categories.html', categories=categories)

@app.route('/categories/delete/<int:cid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def delete_category(cid):
    try:
        cur = mysql.connection.cursor()
        count = repo.count_medicines_in_category(cur, cid)
        if count > 0:
            cur.close()
            flash(f'Cannot delete! {count} medicine(s) use this category', 'danger')
            return redirect(url_for('manage_categories'))

        repo.delete_category(cur, cid)
        audit(cur, 'category.delete', 'category', cid, '')
        mysql.connection.commit()
        cur.close()
        flash('Category deleted successfully', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')
    return redirect(url_for('manage_categories'))

# ---------- CATEGORY QUICK ADD ----------
@app.route('/categories/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def add_category():
    try:
        d = request.form
        name = d['category_name'].strip()

        if not name:
            flash('Category name is required', 'danger')
            return redirect(url_for('medicines'))

        cur = mysql.connection.cursor()
        if repo.category_name_exists(cur, name):
            cur.close()
            flash('Category already exists', 'warning')
            return redirect(url_for('medicines'))

        repo.insert_category(cur, name)
        audit(cur, 'category.add', 'category', None, name)
        mysql.connection.commit()
        cur.close()
        flash('Category added successfully', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')

    return redirect(url_for('medicines'))

# ---------- CUSTOMERS ----------
@app.route('/customers')
@login_required
@guarded
def customers():
    cur = mysql.connection.cursor()
    data = repo.list_customers(cur)
    cur.close()
    return render_template('customers.html', customers=data)

@app.route('/customers/add', methods=['POST'])
@login_required
@guarded
def add_customer():
    try:
        d = request.form
        cur = mysql.connection.cursor()
        repo.insert_customer(cur, d['name'], d['contact'], d['email'], d['gender'], d['history'])
        audit(cur, 'customer.add', 'customer', None, d['name'].strip())
        mysql.connection.commit()
        cur.close()
        flash('Customer added', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')

    referrer = request.referrer or ''
    if 'sales/new' in referrer:
        return redirect(url_for('new_sale'))
    return redirect(url_for('customers'))

@app.route('/customers/delete/<int:cid>', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def delete_customer(cid):
    try:
        cur = mysql.connection.cursor()
        repo.delete_customer(cur, cid)
        audit(cur, 'customer.delete', 'customer', cid, '')
        mysql.connection.commit()
        cur.close()
        flash('Customer deleted', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')
    return redirect(url_for('customers'))

# ---------- SUPPLIERS ----------
@app.route('/suppliers')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def suppliers():
    cur = mysql.connection.cursor()
    data = repo.list_suppliers(cur)
    cur.close()
    return render_template('suppliers.html', suppliers=data)

@app.route('/suppliers/add', methods=['POST'])
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def add_supplier():
    try:
        d = request.form
        cur = mysql.connection.cursor()
        repo.insert_supplier(cur, d['name'], d['contact'], d['email'], d['address'])
        audit(cur, 'supplier.add', 'supplier', None, d['name'].strip())
        mysql.connection.commit()
        cur.close()
        flash('Supplier added successfully', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')

    referrer = request.referrer or ''
    if 'purchase/new' in referrer:
        return redirect(url_for('new_purchase'))
    return redirect(url_for('suppliers'))

@app.route('/suppliers/delete/<int:sid>', methods=['POST'])
@login_required
@role_required('Admin')
@guarded
def delete_supplier(sid):
    try:
        cur = mysql.connection.cursor()
        repo.delete_supplier(cur, sid)
        audit(cur, 'supplier.delete', 'supplier', sid, '')
        mysql.connection.commit()
        cur.close()
        flash('Supplier deleted', 'success')
    except Exception as e:
        flash_unexpected('Something went wrong.')
    return redirect(url_for('suppliers'))
