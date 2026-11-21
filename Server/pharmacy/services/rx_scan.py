"""Prescription photo intake (v76). No Flask, no database except what the caller passes in.

Rules:
- A photo is only a SOURCE of suggestions. Nothing is saved from here.
- The system copies what it reads and matches medicine names. It does not diagnose, choose doses or add items.
- Photos are kept in a private temp folder (not under /static), with random names, and deleted after
  a save, a cancel, or one hour.
- OCR is optional. Without an OCR engine the review page is empty and staff type the rows.
"""
import logging
import glob
import os
import re
import secrets
import shutil
import subprocess
import time
from difflib import SequenceMatcher

from config import Config

TMP_DIR = os.path.join(Config.BASE_DIR, 'instance', 'rx_tmp')
MAX_BYTES = 5 * 1024 * 1024
TTL_SECONDS = 3600
MAX_SUGGESTIONS = 30
_TOKEN = re.compile(r'^[a-f0-9]{32}$')
_EXT_MIME = {'jpg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}


def sniff_type(data):
    """Check the real file type from its first bytes (the file name is not trusted)."""
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    return None


def _ensure_dir():
    os.makedirs(TMP_DIR, exist_ok=True)


def cleanup(now=None):
    """Delete photos older than TTL_SECONDS."""
    if not os.path.isdir(TMP_DIR):
        return 0
    now = time.time() if now is None else now
    removed = 0
    for path in glob.glob(os.path.join(TMP_DIR, '*')):
        try:
            if now - os.path.getmtime(path) > TTL_SECONDS:
                os.remove(path)
                removed += 1
        except OSError as exc:
            logging.getLogger('medigen.rx_scan').warning('could not clean temp file (%s)', type(exc).__name__)
    return removed


def save_upload(data, ext):
    """Store the photo under a random token. Returns the token."""
    _ensure_dir()
    cleanup()
    token = secrets.token_hex(16)
    with open(os.path.join(TMP_DIR, f'{token}.{ext}'), 'wb') as fh:
        fh.write(data)
    return token


def image_path(token):
    """Full path for a valid token, or None (bad token, or expired/deleted photo)."""
    if not isinstance(token, str) or not _TOKEN.match(token):
        return None
    found = glob.glob(os.path.join(TMP_DIR, token + '.*'))
    return found[0] if found else None


def mime_for(path):
    return _EXT_MIME.get(path.rsplit('.', 1)[-1], 'application/octet-stream')


def delete(token):
    path = image_path(token)
    if path:
        try:
            os.remove(path)
        except OSError as exc:
            logging.getLogger('medigen.rx_scan').warning('could not delete prescription image (%s)', type(exc).__name__)


def _tesseract_exe():
    """v84: TESSERACT_CMD in .env wins (full path to tesseract.exe). Else PATH. Else the default Windows install folder."""
    configured = (os.environ.get('TESSERACT_CMD') or '').strip().strip('"')
    if configured and os.path.isfile(configured):
        return configured
    found = shutil.which('tesseract')
    if found:
        return found
    default = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    return default if os.path.isfile(default) else None


def extract_lines(path):
    """Returns (provider, lines, note). Uses Tesseract when it is installed; otherwise no text."""
    exe = _tesseract_exe()
    if not exe:
        return 'none', [], 'No OCR engine on this PC. Type the medicines in the review below.'
    try:
        out = subprocess.run([exe, path, 'stdout'], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return 'tesseract', [], 'OCR could not read this photo. Type the medicines below.'
    lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    return 'tesseract', lines, ('' if lines else 'OCR found no text. Type the medicines below.')


def _norm(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', (text or '').lower())).strip()


def _find_medicine(tokens, medicines):
    """Returns (start, end, medicine_id, name, how) using token positions in the line, or None."""
    norm_toks = [_norm(t) for t in tokens]
    best = None
    for mid, name in medicines:
        nt = _norm(name).split()
        if not nt:
            continue
        for i in range(len(norm_toks) - len(nt) + 1):
            if norm_toks[i:i + len(nt)] == nt and (best is None or len(nt) > best[1] - best[0]):
                best = (i, i + len(nt), mid, name, 'exact')
    if best:
        return best
    close = None
    for size in (3, 2, 1):
        for i in range(0, len(norm_toks) - size + 1):
            window = ' '.join(norm_toks[i:i + size]).strip()
            if len(window) < 4:
                continue
            for mid, name in medicines:
                nn = _norm(name)
                if not nn:
                    continue
                ratio = SequenceMatcher(None, window, nn).ratio()
                if ratio >= 0.85 and (close is None or ratio > close[0]):
                    close = (ratio, i, i + size, mid, name)
        if close:
            break
    if close:
        return (close[1], close[2], close[3], close[4], 'close')
    return None


_DAYS = re.compile(r'(\d{1,3})\s*(?:days?|din)\b', re.IGNORECASE)


def suggest(lines, medicines):
    """Turn OCR lines into review rows. medicines = [(medicine_id, name), ...].
    Each row: line, medicine_id (or None), medicine_name, dosage (copied text), days, match."""
    rows = []
    for raw in lines:
        if len(rows) >= MAX_SUGGESTIONS:
            break
        if sum(ch.isalpha() for ch in raw) < 3:
            continue
        tokens = raw.split()
        found = _find_medicine(tokens, medicines)
        days = 3
        dm = _DAYS.search(raw)
        if dm and 1 <= int(dm.group(1)) <= 365:
            days = int(dm.group(1))
        if found:
            start, end, mid, name, how = found
            rest = tokens[:start] + tokens[end:]
        else:
            mid, name, how, rest = None, '', 'none', tokens
        dosage = _DAYS.sub('', ' '.join(rest))
        dosage = re.sub(r'\bfor\s*$', '', dosage.strip(), flags=re.IGNORECASE)
        dosage = re.sub(r'\s+', ' ', dosage).strip(' .,;:-')[:100]
        rows.append({'line': raw[:200], 'medicine_id': mid, 'medicine_name': name,
                     'dosage': dosage, 'days': days, 'match': how})
    return rows


# v87.06: readiness check for the photo reader. Looks at Tesseract once a minute, not on every page load.
_OCR_CACHE = {'at': 0.0, 'value': None}
OCR_CHECK_TTL = 60
OCR_LANG = 'eng'


def _check_tesseract():
    exe = _tesseract_exe()
    if not exe:
        return {'ready': False, 'exe': None, 'version': '', 'languages': [],
                'message': 'Tesseract was not found on this PC. Photo reading is off. Type the medicines in the review step.'}
    try:
        ver = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=10)
        langs = subprocess.run([exe, '--list-langs'], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return {'ready': False, 'exe': exe, 'version': '', 'languages': [],
                'message': 'Tesseract was found but could not be started. Check the installation.'}
    version = ((ver.stdout or ver.stderr or '').splitlines() or [''])[0].strip()
    languages = [ln.strip() for ln in (langs.stdout or langs.stderr or '').splitlines()
                 if ln.strip() and not ln.lower().startswith('list of available')]
    if OCR_LANG not in languages:
        return {'ready': False, 'exe': exe, 'version': version, 'languages': languages,
                'message': f"Tesseract is installed but the '{OCR_LANG}' language data is missing. Reinstall with English selected."}
    return {'ready': True, 'exe': exe, 'version': version, 'languages': languages,
            'message': 'Photo reading is ready.'}


def ocr_status(force=False):
    """Returns {'ready', 'exe', 'version', 'languages', 'message'}. Cached for OCR_CHECK_TTL seconds."""
    import time as _t
    now = _t.time()
    if force or _OCR_CACHE['value'] is None or now - _OCR_CACHE['at'] > OCR_CHECK_TTL:
        _OCR_CACHE['value'] = _check_tesseract()
        _OCR_CACHE['at'] = now
    return _OCR_CACHE['value']
