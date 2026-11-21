"""Pure helpers for Step 5 (no Flask, no database): phone numbers and reminder text."""
import re
from urllib.parse import quote

DUE_EPS = 0.004      # less than half a paisa counts as paid


def normalize_pk_phone(raw):
    """Pakistani mobile to international form without '+'. Returns '' if it does not look valid.
    Examples: '0300-1234567' -> '923001234567', '+92 300 1234567' -> '923001234567', '3001234567' -> '923001234567'."""
    digits = re.sub(r'\D', '', raw or '')
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('0') and len(digits) == 11:
        digits = '92' + digits[1:]
    elif len(digits) == 10 and digits.startswith('3'):
        digits = '92' + digits
    if len(digits) == 12 and digits.startswith('92') and digits[2] == '3':
        return digits
    return ''


def udhaar_message(name, due, shop):
    """English reminder for udhaar. Amount in rupees, 2 decimals."""
    first = (name or '').strip().split(' ')[0] or 'Sir/Madam'
    return (f"Dear {first}, this is a friendly reminder from {shop}. "
            f"Your balance of Rs. {due:,.2f} is still pending. Please clear it at your earliest convenience. Thank you.")


def whatsapp_link(phone_raw, message):
    """wa.me link with the message filled in, or '' when the number is not valid."""
    number = normalize_pk_phone(phone_raw)
    if not number:
        return ''
    return f"https://wa.me/{number}?text={quote(message)}"
