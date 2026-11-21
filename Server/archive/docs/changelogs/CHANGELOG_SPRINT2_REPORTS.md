# MediGen AI Pro - Sprint 2: Excel, PDF and Sales Tax Summary

## Added
- Reports export to **Excel (.xlsx)** and **PDF** as well as CSV. The Sales tab has Excel and PDF buttons.
- **Sales tax summary** (Admin): one line per day with subtotal, discount, tax, total and returns, plus totals at the bottom. Available as Excel and PDF from the Sales tab.
- The tax summary says plainly that tax on returned sales is not reversed automatically, and that the rate and filing rules must be confirmed by the tax advisor.
- New file `pharmacy/exports.py` builds the Excel and PDF files (no database code, easy to test).
- `requirements.txt`: added `openpyxl` and `reportlab`.

## Test
- `tests/test_sprint2_exports.py`: 19 checks (file formats, numbers kept as numbers, summary and notes, empty reports, wiring).
- Full suite: 520 passed, 0 failed.

## Install
1. Replace the project folder.
2. `pip install -r requirements.txt` (adds openpyxl and reportlab).
3. `python app.py`, then Ctrl+F5.
