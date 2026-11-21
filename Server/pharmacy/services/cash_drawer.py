"""Cash drawer maths (v86.60). Pure functions: no database, so they can be tested directly.

expected = opening + cash sales - cash refunds + cash in - cash out
shortage = counted - expected   (negative = cash is short, positive = extra cash)
"""


def expected_cash(opening, cash_sales, cash_refunds, cash_in, cash_out):
    return round(float(opening) + float(cash_sales) - float(cash_refunds) + float(cash_in) - float(cash_out), 2)


def shortage(counted, expected):
    return round(float(counted) - float(expected), 2)


def describe(diff):
    """Short Roman Urdu/English label for the closing result."""
    if diff < -0.004:
        return ('short', f'Cash short by Rs. {abs(diff):,.0f}.')
    if diff > 0.004:
        return ('extra', f'Extra cash of Rs. {diff:,.0f}.')
    return ('ok', 'Cash matches exactly.')


CASH_LOCK_TEXT = 'The cash drawer is closed. Open the drawer {what}, or use another payment method.'


def lock_message(drawer_is_open, method, amount, what):
    """v87.03 cash lock. Cash taken or paid out while the drawer is closed would never reach the drawer count,
    so it is refused. Card, Online and zero amounts are not affected. Returns the message, or None."""
    if drawer_is_open or method != 'Cash' or not amount or float(amount) <= 0:
        return None
    return CASH_LOCK_TEXT.format(what=what)
