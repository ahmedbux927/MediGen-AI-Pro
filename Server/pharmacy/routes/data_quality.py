"""Routes: Data Quality report (v86.46). Read only, so it never changes a record."""
from pharmacy.core import *  # noqa: F401,F403
from pharmacy.lib import *  # noqa: F401,F403
from pharmacy.repos import data_quality as repo


@app.route('/data-quality')
@login_required
@role_required('Admin', 'Pharmacist')
@guarded
def data_quality():
    cur = mysql.connection.cursor()
    total = repo.live_count(cur)
    checks = [
        ('duplicate', 'Same name twice', 'Same medicine may be entered twice. Check and merge.', repo.duplicate_names(cur)),
        ('category', 'No category', 'Pick a category so reports and sections are correct.', repo.missing_category(cur)),
        ('negative', 'Negative stock', 'Sold more than the recorded stock (usually an offline bill synced later). Count the shelf and correct the stock.', repo.negative_stock(cur)),
        ('price', 'No price or zero price', 'Sale price is missing, so billing may be wrong.', repo.missing_price(cur)),
        ('form', 'No dosage form', 'Dosage form decides the section (Syrup, Cream, Drip, Other).', repo.missing_dosage_form(cur)),
        ('strength', 'Bad strength', 'Strength like "0" or only a number (no mg/ml). Fix with Edit.', repo.bad_strength(cur)),
        ('repeat_cat', 'Repeated categories', 'Same category name with different spelling or case.', repo.repeated_categories(cur)),
        ('barcode', 'Same barcode on two items', 'One barcode must belong to one medicine. Edit one of them and change or clear the barcode.', repo.duplicate_barcodes(cur)),
        ('no_batch', 'Stock but no batch', 'Has stock but no batch, so expiry is unknown. Use Edit selected > Expiry.', repo.stock_without_batch(cur)),
        ('mismatch', 'Stock and batches differ', 'Medicine stock and batch total do not match.', repo.stock_batch_mismatch(cur)),
    ]
    cur.close()
    # a medicine counts once even if it has several problems; duplicate names and
    # repeated categories are groups, not single medicines, so they are not counted here
    item_ids = set()
    for key, _, _, rows in checks:
        if key in ('duplicate', 'repeat_cat', 'barcode'):
            continue
        item_ids.update(r['medicine_id'] for r in rows)
    clean = max(0, total - len(item_ids))
    score = round(100 * clean / total) if total else 100
    return render_template('data_quality.html', checks=checks, total=total, score=score,
                           clean=clean, shop=get_setting('shop_name'))
