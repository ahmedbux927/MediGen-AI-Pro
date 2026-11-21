"""Seasonal purchase forecast (v87.12). Rules only, no AI. Suggests; never orders.

For each medicine:
- recent   = units sold in the last 30 days (net of returns)
- last_year = units sold in the same 30 days one year ago (the season that is coming)
- expected next 30 days = the higher of the two daily rates x 30, so a season is not missed
- seasonal = last year's window is at least 1.5x the recent window and at least MIN_SEASON_UNITS
Suggested quantity = target stock (expected, but not below the reorder level) minus stock on hand.
"""
import math

COVER_DAYS = 30
SEASON_RATIO = 1.5
MIN_SEASON_UNITS = 5


def forecast(recent, last_year, stock, reorder, cover_days=COVER_DAYS):
    recent = max(0, int(recent or 0))
    last_year = max(0, int(last_year or 0))
    stock = max(0, int(stock or 0))
    reorder = max(0, int(reorder or 0))
    if recent == 0 and last_year == 0:
        return {'expected': 0, 'suggested': 0, 'seasonal': False, 'reason': 'No sales in the last year for this window.'}
    rate = max(recent, last_year) / 30.0
    expected = math.ceil(rate * cover_days)
    seasonal = last_year >= MIN_SEASON_UNITS and last_year >= SEASON_RATIO * max(recent, 1)
    target = max(expected, reorder)
    suggested = max(0, target - stock)
    if seasonal:
        reason = f'Season: {last_year} units sold in the same 30 days last year, {recent} in the last 30 days.'
    else:
        reason = f'Recent sales: {recent} units in the last 30 days.'
    return {'expected': expected, 'suggested': suggested, 'seasonal': seasonal, 'reason': reason}
