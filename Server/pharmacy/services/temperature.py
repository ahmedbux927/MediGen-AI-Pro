"""Cold-chain temperature checks (Phase 4 backend). Pure rules + one insert. The caller commits.

Default range 2 to 8 degrees C (fridge for insulin, injections, vaccines). Each location can have its own range.
A reading outside the range is still saved, with in_range = 0, so the owner sees it in the daily report.
"""
from decimal import Decimal, InvalidOperation

DEFAULT_MIN_C = Decimal('2.0')
DEFAULT_MAX_C = Decimal('8.0')


class TemperatureError(ValueError):
    """A reading the user must correct. The message is shown as it is."""


def parse_reading(text):
    try:
        t = Decimal(str(text).strip().replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise TemperatureError('Temperature must be a number, for example 5.2')
    if t < Decimal('-40') or t > Decimal('60'):
        raise TemperatureError('Temperature looks wrong (outside -40 to 60 C). Please check the thermometer and try again.')
    return t.quantize(Decimal('0.1'))


def is_in_range(temp, low=DEFAULT_MIN_C, high=DEFAULT_MAX_C):
    return low <= temp <= high


def record_reading(cur, location, text, user_id, note='', low=DEFAULT_MIN_C, high=DEFAULT_MAX_C):
    if not location or not location.strip():
        raise TemperatureError('Please name the place where the reading was taken (for example Fridge 1).')
    temp = parse_reading(text)
    ok = is_in_range(temp, low, high)
    cur.execute("""INSERT INTO temperature_logs (location, temperature_c, in_range, user_id, note)
                   VALUES (%s,%s,%s,%s,%s)""", (location.strip()[:40], temp, 1 if ok else 0, user_id, (note or '')[:200] or None))
    return {'temperature': temp, 'in_range': ok, 'log_id': cur.lastrowid}
