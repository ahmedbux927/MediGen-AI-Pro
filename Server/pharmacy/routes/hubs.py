"""Routes: group hub pages behind the sidebar (v87.16). Each hub lists its links as cards, filtered by role."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403

ALL = ('Admin', 'Pharmacist', 'Cashier')
ADMIN_PH = ('Admin', 'Pharmacist')
ADMIN = ('Admin',)

# (label, icon, endpoint, description, roles, url kwargs)
GROUPS = {
    'medicines': ('Pharmacy Catalog', 'Every medicine and product, by section', [
        ('All Medicines', 'bi-capsule', 'medicines', 'Full medicine list and search', ALL, {}),
        ('Syrups & Suspensions', 'bi-cup-straw', 'products_section', 'Syrups and suspensions', ALL, {'key': 'syrups'}),
        ('Creams & Gels', 'bi-droplet', 'products_section', 'Creams and gels', ALL, {'key': 'creams'}),
        ('Drip & Injection', 'bi-droplet-half', 'products_section', 'Drip and injection records', ALL, {'key': 'drip'}),
        ('Bandages & Other Products', 'bi-bandaid', 'products_section', 'Everything else', ALL, {'key': 'other'}),
    ]),
    'inventory': ('Inventory', 'Stock, batches and checks', [
        ('Stock Overview', 'bi-grid-1x2', 'products_hub', 'All products and stock levels', ALL, {}),
        ('Batches & Expiry', 'bi-calendar-x', 'batches', 'Batches and expiry dates', ALL, {}),
        ('Expired & Alerts', 'bi-bell', 'alerts', 'Expired and low-stock alerts', ALL, {}),
        ('Cold Chain Log', 'bi-thermometer-half', 'cold_chain', 'Fridge temperature records', ALL, {}),
        ('Stock Count', 'bi-clipboard-data', 'stock_count_home', 'Physical stock counts', ADMIN_PH, {}),
        ('Categories', 'bi-tags', 'manage_categories', 'Product categories', ADMIN_PH, {}),
        ('Controlled Register', 'bi-shield-lock', 'controlled_register', 'Controlled drug register', ADMIN_PH, {}),
    ]),
    'sales': ('Sales & Billing', 'Bills, customers and prescriptions', [
        ('New Sale', 'bi-plus-circle', 'new_sale', 'Start a new bill (POS)', ALL, {}),
        ('Sales History', 'bi-cart', 'sales', 'Past bills and returns', ALL, {}),
        ('Cash Drawer', 'bi-cash-stack', 'cash_drawer', 'Open, close and count the drawer', ALL, {}),
        ('Customers', 'bi-people', 'customers', 'Customer list and phone numbers', ALL, {}),
        ('Customer Dues', 'bi-cash-coin', 'customer_dues', 'Udhaar and repayments', ADMIN_PH, {}),
        ('Prescriptions', 'bi-file-medical', 'prescriptions', 'Prescription records', ADMIN_PH, {}),
        ('Drug Interactions', 'bi-exclamation-diamond', 'interactions', 'Warning pairs for bills', ADMIN_PH, {}),
    ]),
    'purchasing': ('Purchasing', 'Suppliers, orders and forecasts', [
        ('Suppliers', 'bi-truck', 'suppliers', 'Supplier list', ADMIN_PH, {}),
        ('Purchases', 'bi-bag', 'purchase', 'Goods received from suppliers', ADMIN, {}),
        ('Suggestions', 'bi-cart-plus', 'purchase_suggestions', 'Items to reorder', ADMIN, {}),
        ('Purchase Drafts', 'bi-cart-plus', 'purchase_drafts', 'Draft orders per supplier', ADMIN_PH, {}),
        ('Purchase Forecast', 'bi-graph-up-arrow', 'purchase_forecast', 'Seasonal order suggestions', ADMIN_PH, {}),
        ('Supplier Returns', 'bi-arrow-return-left', 'supplier_returns', 'Goods sent back to suppliers', ADMIN_PH, {}),
        ('Supplier Summary', 'bi-journal-text', 'supplier_summary', 'Balances per supplier', ADMIN_PH, {}),
    ]),
    'finance': ('Finance', 'Expenses, closing, margins and reports', [
        ('Expenses', 'bi-receipt', 'expenses', 'Shop expenses', ADMIN_PH, {}),
        ('Daily Closing', 'bi-journal-check', 'daily_closing', 'End-of-day totals', ADMIN_PH, {}),
        ('Profit Margin', 'bi-percent', 'margins', 'Margin per item', ADMIN_PH, {}),
        ('Reports', 'bi-graph-up', 'reports', 'Sales and stock reports', ADMIN, {}),
        ('Inspection Report', 'bi-file-earmark-spreadsheet', 'inspection_report', 'Excel for drug inspection: controlled, cold chain, write-offs', ADMIN_PH, {}),
    ]),
    'admin': ('Admin', 'Settings, users and shop tools', [
        ('Daily Digest', 'bi-journal-text', 'daily_digest', 'Roz ka khulasa: sale, stock, udhaar, backup', ADMIN, {}),
        ('Settings', 'bi-gear', 'settings_page', 'Shop settings', ADMIN, {}),
        ('Users', 'bi-person-gear', 'users', 'Staff accounts and roles', ADMIN, {}),
        ('Activity Log', 'bi-journal-text', 'activity_log', 'Who did what, and when', ADMIN, {}),
        ('Data Quality', 'bi-clipboard2-check', 'data_quality', 'Find and fix data problems', ADMIN, {}),
        ('Records Clear', 'bi-trash', 'records_clear', 'Clear old records', ADMIN, {}),
    ]),
}

ROLE_GATE = {'medicines': ALL, 'inventory': ALL, 'sales': ALL, 'purchasing': ADMIN_PH, 'finance': ADMIN_PH, 'admin': ADMIN_PH}


def _cards(key, role):
    out = []
    for label, icon, endpoint, desc, roles, kw in GROUPS[key][2]:
        if role in roles:
            out.append({'label': label, 'icon': icon, 'desc': desc, 'url': url_for(endpoint, **kw)})
    return out


def _render(key):
    title, intro, _ = GROUPS[key]
    return render_template('hub.html', page_title=title, heading=title, intro=intro,
                           cards=_cards(key, session.get('role')))


@app.route('/medicines-hub')
@login_required
@role_required(*ALL)
@guarded
def medicines_hub():
    return _render('medicines')


@app.route('/inventory-hub')
@login_required
@role_required(*ALL)
@guarded
def inventory_hub():
    return _render('inventory')


@app.route('/sales-billing')
@login_required
@role_required(*ALL)
@guarded
def sales_hub():
    return _render('sales')


@app.route('/purchasing-hub')
@login_required
@role_required(*ADMIN_PH)
@guarded
def purchasing_hub():
    return _render('purchasing')


@app.route('/finance')
@login_required
@role_required(*ADMIN_PH)
@guarded
def finance_hub():
    return _render('finance')


@app.route('/admin-hub')
@login_required
@role_required(*ADMIN_PH)
@guarded
def admin_hub():
    return _render('admin')
