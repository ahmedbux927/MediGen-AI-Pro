"""v72: turns a chat message into a WRITE proposal for the AI agent. No Flask, no database.

Only two write commands are understood (both go through agent_tools.propose, then need a Confirm click):
  - shelf:     "shelf Panadol to A-3"  /  "Panadol ka shelf A-3"  /  "Panadol shelf = A-3"
  - customer:  "add customer Ali Khan 0300-1234567"  /  "naya customer Ali"
Read-only (no confirmation needed):
  - where:     "shelf Panadol" / "Panadol ka shelf" / "where is Panadol" / "kahan hai Panadol"
  - phone:     "0300-1234567" / "customer 03001234567"  (digits only, 4 or more)
Anything else returns None, so the normal chat engine answers it.
"""
import re

_SHELF_1 = re.compile(r"^(?:set\s+|update\s+)?(?:shelf|rack)\s+(?:of\s+|for\s+)?(.+?)\s+(?:to|=|ko|mein|me)\s+"
                      r"([A-Za-z0-9][A-Za-z0-9\-/ ]{0,39})$", re.IGNORECASE)
_SHELF_2 = re.compile(r"^(.+?)\s+(?:ka\s+|ki\s+)?(?:shelf|rack)\s*(?:to|=|ko)?\s+"
                      r"([A-Za-z0-9][A-Za-z0-9\-/]{0,39})$", re.IGNORECASE)
_CUSTOMER = re.compile(r"^(?:add|new|naya|nayi)\s+customer\s+(.+)$", re.IGNORECASE)
_PHONE_END = re.compile(r"\s+(\+?\d[\d\- ]{5,18}\d)$")


def parse_write(message):
    """Return None (not a write command), {'error': text}, or
    {'action': ..., 'params': {...}, 'medicine_name': ...} for a proposal."""
    text = re.sub(r"\s+", " ", (message or "")).strip()
    if not text:
        return None
    m = _SHELF_1.match(text) or _SHELF_2.match(text)
    if m:
        name, shelf = m.group(1).strip(), m.group(2).strip()
        if not name:
            return {'error': 'Please enter the medicine name. Example: shelf Panadol to A-3'}
        return {'action': 'set_shelf_location', 'medicine_name': name,
                'params': {'shelf_location': shelf}}
    m = _CUSTOMER.match(text)
    if m:
        rest = m.group(1).strip()
        contact = None
        pm = _PHONE_END.search(rest)
        if pm:
            contact = re.sub(r"[\s\-]", "", pm.group(1))
            rest = rest[:pm.start()].strip()
        if not rest:
            return {'error': 'Please enter the customer name. Example: add customer Ali Khan 0300-1234567'}
        params = {'name': rest[:100]}
        if contact:
            params['contact_number'] = contact
        return {'action': 'add_customer', 'params': params}
    return None


_SHELF_Q_1 = re.compile(r"^(?:shelf|rack)\s+(?:of\s+|for\s+)?(.+?)\s*\??$", re.IGNORECASE)
_SHELF_Q_2 = re.compile(r"^(.+?)\s+(?:ka\s+|ki\s+)?(?:shelf|rack)\s*\??$", re.IGNORECASE)
_WHERE_Q = re.compile(r"^(?:where\s+is|kahan\s+(?:hai|h)?|kahan|kidhar)\s+(.+?)\s*\??$", re.IGNORECASE)
_PHONE_Q = re.compile(r"^(?:customer\s+|gahak\s+)?(\+?[\d][\d\- ]{2,18}[\d])$", re.IGNORECASE)


def parse_read(message):
    """Return None, or {'read': 'medicine_shelf', 'text': name} / {'read': 'customer_phone', 'text': digits}."""
    text = re.sub(r"\s+", " ", (message or "")).strip()
    if not text or parse_write(text) is not None:
        return None
    m = _PHONE_Q.match(text)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) >= 4:
            return {'read': 'customer_phone', 'text': m.group(1).strip()}
        return None
    for rx in (_SHELF_Q_1, _SHELF_Q_2, _WHERE_Q):
        m = rx.match(text)
        if m and m.group(1).strip():
            return {'read': 'medicine_shelf', 'text': m.group(1).strip()[:80]}
    return None


def _shelf_line(r):
    shelf = r.get('rack_location') or 'shelf not set'
    return f"• **{r['name']}**: shelf {shelf}, stock {int(r.get('stock_quantity') or 0)}, Rs. {float(r.get('price') or 0):,.0f}"


def shelf_answer(rows, text):
    """Plain text answer for a shelf / stock question. rows come from agent_tools.find_medicine."""
    if not rows:
        return f"No medicine found: '{text}'. Try again with part of the name."
    if len(rows) == 1:
        return _shelf_line(rows[0])
    return f"**{len(rows)} medicines found**\n" + "\n".join(_shelf_line(r) for r in rows[:10])


def customer_answer(rows, text):
    """Plain text answer for a phone search. rows come from phone_search.search_customers."""
    if not rows:
        return f"No customer found for this number: {text}. To add a new customer, type 'add customer NAME {text}'."
    lines = []
    for r in rows[:8]:
        bal = float(r.get('balance') or 0)
        due = f", owes Rs. {bal:,.0f}" if bal > 0.004 else ''
        lines.append(f"• **{r['name']}** {r.get('contact_number') or ''}{due}")
    return f"**{len(rows)} customer mile**\n" + "\n".join(lines)
