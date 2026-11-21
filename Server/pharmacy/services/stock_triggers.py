"""Stock triggers (v83). No Flask in this file.

A sale lowers stock and a purchase raises it, and the sale code relies on these two triggers
(see services/sales.py save_sale). If the database lacks them, sales are saved but stock never moves.
The app checks them at startup and creates a missing one.

A table is "covered" when ANY insert trigger already exists on it (under any name), so a trigger
is never added twice, which would take the stock twice.
"""

SALE_TRIGGER = ('trg_sale_stock', 'sale_items',
                "CREATE TRIGGER trg_sale_stock AFTER INSERT ON sale_items FOR EACH ROW BEGIN "
                "UPDATE medicines SET stock_quantity = stock_quantity - NEW.quantity WHERE medicine_id = NEW.medicine_id; "
                "UPDATE batches SET quantity = quantity - NEW.quantity WHERE batch_id = NEW.batch_id; END")
PURCHASE_TRIGGER = ('trg_purchase_stock', 'purchase_items',
                    "CREATE TRIGGER trg_purchase_stock AFTER INSERT ON purchase_items FOR EACH ROW BEGIN "
                    "UPDATE medicines SET stock_quantity = stock_quantity + NEW.quantity WHERE medicine_id = NEW.medicine_id; END")
REQUIRED = [SALE_TRIGGER, PURCHASE_TRIGGER]


def missing(existing):
    """existing = [(trigger_name, table_name), ...] for INSERT triggers. Returns [(name, table, ddl), ...] to create."""
    covered = {table for _, table in existing}
    return [(name, table, ddl) for name, table, ddl in REQUIRED if table not in covered]
