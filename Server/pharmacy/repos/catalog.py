"""SQL for categories, customers and suppliers."""


def list_categories(cur):
    cur.execute("SELECT * FROM categories ORDER BY category_id ASC")
    return cur.fetchall()


def category_name_exists(cur, name):
    cur.execute("SELECT category_id FROM categories WHERE category_name = %s", (name,))
    return cur.fetchone() is not None


def insert_category(cur, name):
    cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (name,))


def count_medicines_in_category(cur, cid):
    cur.execute("SELECT COUNT(*) AS c FROM medicines WHERE category_id = %s", (cid,))
    return cur.fetchone()['c']


def delete_category(cur, cid):
    cur.execute("DELETE FROM categories WHERE category_id = %s", (cid,))


def list_customers(cur):
    cur.execute("SELECT * FROM customers ORDER BY customer_id ASC")
    return cur.fetchall()


def insert_customer(cur, name, contact, email, gender, history):
    cur.execute("""INSERT INTO customers (name, contact_number, email, gender, medical_history)
                   VALUES (%s,%s,%s,%s,%s)""", (name, contact, email, gender, history))


def delete_customer(cur, cid):
    cur.execute("DELETE FROM customers WHERE customer_id=%s", (cid,))


def list_suppliers(cur):
    cur.execute("SELECT * FROM suppliers ORDER BY supplier_id ASC")
    return cur.fetchall()


def insert_supplier(cur, name, contact, email, address):
    cur.execute("""INSERT INTO suppliers (name, contact, email, address)
                   VALUES (%s,%s,%s,%s)""", (name, contact, email, address))


def delete_supplier(cur, sid):
    cur.execute("DELETE FROM suppliers WHERE supplier_id=%s", (sid,))
