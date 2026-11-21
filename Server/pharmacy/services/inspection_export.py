"""Inspection report rows (Stage 3, item D). Pure merge rules - no Flask, no MySQL.

One list for a drug inspector covering a date range:
  - controlled drug register entries
  - cold chain temperature readings
  - expiry write-offs (stock removed because the batch expired)
The SQL that feeds these rows and the Excel/PDF download are built separately.
"""
from datetime import datetime

HEADERS = ['Date and time', 'Section', 'Item or location', 'Detail', 'Quantity', 'Batch',
           'Customer', 'Staff', 'Status or note']


def _text(v):
    return '' if v is None else str(v)


def _when(v):
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return datetime.min


def controlled_rows(entries):
    out = []
    for e in entries or []:
        out.append({
            'when': _when(e.get('created_at')), 'section': 'Controlled drug',
            'item': _text(e.get('medicine_name')), 'detail': 'Schedule ' + _text(e.get('schedule')),
            'quantity': e.get('quantity'), 'batch': _text(e.get('batch_number')),
            'customer': _text(e.get('customer_name')), 'staff': _text(e.get('username')),
            'status': 'Sale #' + _text(e.get('sale_id')) if e.get('sale_id') else 'Entry',
        })
    return out


def cold_chain_rows(readings):
    out = []
    for r in readings or []:
        ok = bool(r.get('in_range'))
        out.append({
            'when': _when(r.get('recorded_at')), 'section': 'Cold chain',
            'item': _text(r.get('location')), 'detail': f"{r.get('temperature_c')} C",
            'quantity': None, 'batch': '', 'customer': '', 'staff': _text(r.get('username')),
            'status': 'In range' if ok else 'OUT OF RANGE - ' + (_text(r.get('note')) or 'action needed'),
        })
    return out


def writeoff_rows(adjustments):
    out = []
    for a in adjustments or []:
        out.append({
            'when': _when(a.get('created_at')), 'section': 'Expiry write-off',
            'item': _text(a.get('medicine_name')), 'detail': _text(a.get('note')),
            'quantity': a.get('change_qty'), 'batch': '', 'customer': '',
            'staff': _text(a.get('username')), 'status': 'Removed (expired)',
        })
    return out


def merge(controlled=None, cold=None, writeoffs=None):
    """All sections in one list, oldest first. Each row is a list of strings in HEADERS order."""
    rows = controlled_rows(controlled) + cold_chain_rows(cold) + writeoff_rows(writeoffs)
    rows.sort(key=lambda r: (r['when'], r['section']))
    table = []
    for r in rows:
        when = r['when'].strftime('%Y-%m-%d %H:%M') if r['when'] != datetime.min else ''
        qty = '' if r['quantity'] is None else str(r['quantity'])
        table.append([when, r['section'], r['item'], r['detail'], qty, r['batch'],
                      r['customer'], r['staff'], r['status']])
    return table
