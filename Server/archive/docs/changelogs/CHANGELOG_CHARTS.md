# Charts fix (patch v23)

## Problem
- Dashboard "Last 7 days" bar chart skipped days with no sales, so the bars did not line up with the calendar.
- The query used `INTERVAL 7 DAY`, which covered 8 days, not 7.
- Reports "Daily Revenue Trend" / "Daily Sales" chart also skipped days (the docs said it was filled; the code was not).
- Dashboard "Top sellers" counted sold units before returns, while Reports counted them after returns, so the two pages could disagree.
- Browser Back could show a dashboard or report page from before the latest sale.

## Fix
- `pharmacy/lib.py`: new `_fill_days(rows, start, end, key)` gives one point per calendar day, zero where there were no sales.
- `pharmacy/routes/dashboard.py`: exact 7-day window (today and the 6 days before). Top 5 sellers are now net of returns and only include medicines with units left after returns. Empty-state flag `chart_has_data`. Response sends `Cache-Control: no-store`.
- `pharmacy/routes/reports.py`: the daily chart uses `_fill_days` for the selected range. Response sends `no-store`.
- `templates/dashboard.html`: the sales chart shows "No sales in the last 7 days yet." only when all 7 days are zero.
- `tests/test_charts_data.py`: 12 new checks.

## Files
- pharmacy/lib.py
- pharmacy/routes/dashboard.py
- pharmacy/routes/reports.py
- templates/dashboard.html
- tests/test_charts_data.py
- CHANGELOG_CHARTS.md

## Test result
- Full mock suite: 941 passed, 0 failed.

## Notes
- Charts are drawn from the database on every page load. Refresh or open the page again after a sale to see it.
- A very long reports range (for example several years) gives one point per day, so the line becomes dense. The presets (7 days, 30 days, 1 year) are fine.
