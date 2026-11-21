"""SQL for shop expenses (v86.61). Electricity, salary, tea and water, rent and so on."""

CATEGORIES = ('Electricity', 'Salary', 'Tea and water', 'Rent', 'Transport',
              'Maintenance', 'Other')
PAID_VIA = ('Cash', 'Card', 'Online')


def insert(cur, when, category, amount, paid_via, note, user_id):
    cur.execute("""INSERT INTO expenses (expense_date, category, amount, paid_via, note, user_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""", (when, category, amount, paid_via, note, user_id))
    return cur.lastrowid


def list_for_month(cur, month_start, month_end):
    cur.execute("""SELECT e.expense_id, e.expense_date, e.category, e.amount, e.paid_via, e.note, u.username
                   FROM expenses e LEFT JOIN users u ON u.user_id = e.user_id
                   WHERE e.expense_date BETWEEN %s AND %s
                   ORDER BY e.expense_date DESC, e.expense_id DESC LIMIT 300""", (month_start, month_end))
    return cur.fetchall()


def total_between(cur, start, end):
    cur.execute("""SELECT COALESCE(SUM(amount), 0) AS v FROM expenses
                   WHERE expense_date BETWEEN %s AND %s""", (start, end))
    return float(cur.fetchone()['v'] or 0)


def by_category(cur, start, end):
    cur.execute("""SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses
                   WHERE expense_date BETWEEN %s AND %s GROUP BY category ORDER BY total DESC""", (start, end))
    return cur.fetchall()
