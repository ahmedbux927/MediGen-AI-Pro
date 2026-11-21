"""v76: prescription photo intake. Service checks (temp files, file type, OCR fallback, matching) + wiring. No MySQL.
Run through tests/run_all.py."""
import os as _os, sys, tempfile, shutil
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
import pharmacy.services.rx_scan as R
RESULTS = []
DEFAULT_DIR = R.TMP_DIR   # checked before the tests point TMP_DIR at a temp folder
def ok(c, msg): RESULTS.append((msg, bool(c)))

# file type is read from the bytes, not the name
ok(R.sniff_type(b'\xff\xd8\xff\xe0' + b'x' * 10) == 'jpg', 'JPEG is recognised by its bytes')
ok(R.sniff_type(b'\x89PNG\r\n\x1a\n' + b'x') == 'png', 'PNG is recognised by its bytes')
ok(R.sniff_type(b'RIFF\x00\x00\x00\x00WEBPVP8 ') == 'webp', 'WEBP is recognised by its bytes')
ok(R.sniff_type(b'<html><script>') is None and R.sniff_type(b'MZ\x90\x00') is None, 'HTML and EXE files are refused')
ok(R.sniff_type(b'') is None, 'empty upload is refused')
ok(R.MAX_BYTES == 5 * 1024 * 1024, 'photo limit is 5 MB')

# temp folder: private, random, expires
tmp = tempfile.mkdtemp()
R.TMP_DIR = _os.path.join(tmp, 'rx_tmp')
try:
    tok = R.save_upload(b'\xff\xd8\xff' + b'img', 'jpg')
    ok(len(tok) == 32 and all(c in '0123456789abcdef' for c in tok), 'photo gets a random 32-character token')
    path = R.image_path(tok)
    ok(path and path.endswith('.jpg') and _os.path.exists(path), 'saved photo can be found by its token')
    ok('instance' in DEFAULT_DIR.replace('\\', '/') and 'static' not in DEFAULT_DIR.replace('\\', '/'), 'photos default to the private instance folder, never static/')
    ok(R.image_path('../../etc/passwd') is None and R.image_path('A' * 32) is None and R.image_path(None) is None,
       'bad tokens (path tricks, upper case, empty) are refused')
    ok(R.mime_for(path) == 'image/jpeg', 'served with the right image type')
    R.delete(tok)
    ok(R.image_path(tok) is None, 'delete removes the photo')
    tok2 = R.save_upload(b'\x89PNG\r\n\x1a\nold', 'png')
    removed = R.cleanup(now=_os.path.getmtime(R.image_path(tok2)) + R.TTL_SECONDS + 5)
    ok(removed == 1 and R.image_path(tok2) is None, 'photos older than one hour are removed')
    tok3 = R.save_upload(b'\x89PNG\r\n\x1a\nnew', 'png')
    ok(R.cleanup() == 0 and R.image_path(tok3) is not None, 'fresh photos are kept')
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# OCR: no engine installed -> no lines and a clear note (no crash)
_real_which = R.shutil.which
R.shutil.which = lambda name: None
prov, lines, note = R.extract_lines('/nonexistent.jpg')
R.shutil.which = _real_which
ok(prov == 'none' and lines == [] and 'Type the medicines' in note, 'without an OCR engine the review is empty and says so')

meds = [(1, 'Panadol'), (2, 'Augmentin 625'), (3, 'Brufen')]
rows = R.suggest(['Tab Panadol 500mg 1 tablet twice a day for 5 days'], meds)
ok(rows[0]['medicine_id'] == 1 and rows[0]['match'] == 'exact', 'a known medicine name is matched exactly')
ok(rows[0]['days'] == 5 and 'days' not in rows[0]['dosage'] and rows[0]['dosage'].startswith('Tab 500mg'), 'days are read and removed from the dosage text')
rows = R.suggest(['Brufn 400 one tab night'], meds)
ok(rows[0]['medicine_id'] == 3 and rows[0]['match'] == 'close', 'a small spelling mistake is a close match (staff check the name)')
rows = R.suggest(['Augmentin 625 - 1 tab BD x 7 days'], meds)
ok(rows[0]['medicine_id'] == 2 and rows[0]['days'] == 7, 'two-word medicine names match and their days are read')
rows = R.suggest(['Dr. Ahmed Clinic'], meds)
ok(rows[0]['medicine_id'] is None and rows[0]['match'] == 'none', 'a line with no medicine is shown as not matched, never guessed')
ok(R.suggest(['..', '12', 'ab'], meds) == [], 'very short or number-only lines are ignored')
ok(len(R.suggest(['Panadol 1 tab'] * 50, meds)) == R.MAX_SUGGESTIONS, 'suggestions are capped at 30 rows')
ok(R.suggest(['Panadol 1 tab'], meds)[0]['days'] == 3, 'days default to 3 when the paper does not say')

route = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'rx_scan.py'), encoding='utf-8').read()
save_part = route.split('def rx_scan_save')[1].split('@app.route')[0]
ok("request.form.get('confirmed') != '1'" in save_part, 'save refuses unless the check box is ticked')
ok(save_part.index("request.form.get('confirmed')") < save_part.index('INSERT INTO prescriptions'), 'the check happens before anything is written')
ok('RXS.delete(token)' in save_part, 'the photo is deleted after a successful save')
ok("prescription.scan_add" in save_part, 'the save is written to the audit log')
ok("resp.headers['Cache-Control'] = 'private, no-store'" in route, 'the photo is served as private, not cached')
ok("@role_required('Admin', 'Pharmacist')" in route and route.count('@role_required') == 4, 'every photo route is limited to Admin and Pharmacist')
ok('from . import rx_scan' in open(_os.path.join(ROOT, 'pharmacy', 'routes', '__init__.py'), encoding='utf-8').read(), 'routes are registered')
rev = open(_os.path.join(ROOT, 'templates', 'rx_review.html'), encoding='utf-8').read()
ok('name="confirmed" value="1"' in rev and 'Nothing is saved yet' in rev, 'review page says nothing is saved until the check box is ticked')
ok('name="token"' in rev and 'rx_scan_image' in rev, 'review page shows the photo from the private route')
add = open(_os.path.join(ROOT, 'templates', 'add_prescription.html'), encoding='utf-8').read()
ok("url_for('rx_scan')" in add, 'the add prescription page links to the photo option')

failed = [n for n, g in RESULTS if not g]
for n, g in RESULTS: print(('PASS ' if g else 'FAIL ') + n)
print(f'\nTOTAL: {len(RESULTS) - len(failed)} passed, {len(failed)} failed')
if failed: sys.exit(1)
