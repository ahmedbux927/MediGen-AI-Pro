"""Find a customer by phone number (Phase 2). Pure normalisation + one query. No Flask.

Pakistani numbers are typed many ways: 0300-1234567, +92 300 1234567, 00923001234567, 3001234567.
All of them become the last 10 digits (3001234567) before comparing.
"""
import re

MIN_DIGITS = 4          # a shorter search would list too many customers


def normalise_phone(text):
    """Return the digits to match on, or '' when the text has fewer than MIN_DIGITS digits."""
    digits = re.sub(r'\D', '', text or '')
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('92') and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith('0'):
        digits = digits[1:] if len(digits) == 11 else digits
    if len(digits) > 10:
        digits = digits[-10:]
    return digits if len(digits) >= MIN_DIGITS else ''


SEARCH_SQL = """SELECT c.customer_id, c.name, c.contact_number,
                       (SELECT MAX(s.sale_date) FROM sales s WHERE s.customer_id = c.customer_id) AS last_sale,
                       IFNULL((SELECT SUM(s.total_amount - s.returned_amount - s.paid_amount)
                               FROM sales s WHERE s.customer_id = c.customer_id), 0) AS balance
                FROM customers c
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(IFNULL(c.contact_number, ''), ' ', ''), '-', ''), '+', ''), '.', '') LIKE %s
                ORDER BY c.name ASC LIMIT %s"""


def search_customers(cur, text, limit=10):
    """Returns [] for a search that is too short. Results are capped at 50."""
    digits = normalise_phone(text)
    if not digits:
        return []
    cur.execute(SEARCH_SQL, ('%' + digits + '%', min(max(1, int(limit)), 50)))
    return cur.fetchall()
