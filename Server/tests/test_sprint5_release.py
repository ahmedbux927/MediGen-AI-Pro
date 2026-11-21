"""Sprint 5 checks: Windows launcher, Inno Setup script, help center and guides exist and keep their key settings.
Static checks only (no Inno Setup compiler needed). Run: python tests/test_sprint5_release.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('MEDIGEN_ROOT') or os.path.abspath(os.path.join(HERE, '..'))

PASS = FAIL = 0
def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1; print('PASS', label)
    else:
        FAIL += 1; print('FAIL', label)

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()

for rel in ['scripts/start_medigen.bat', 'installer/MediGen.iss', 'installer/README.md',
            'docs/HELP_CENTER.md', 'docs/VIDEO_SCRIPTS.md', 'REMOVED_PHONE_CODE.md']:
    ok(os.path.exists(os.path.join(ROOT, rel)), f'{rel} exists')

bat = read('scripts/start_medigen.bat')
ok('python desktop.py' in bat and 'pause' in bat, 'launcher starts desktop.py and waits on error')
iss = read('installer/MediGen.iss')
ok('Excludes: ".env' in iss and 'backups' in iss, 'installer never ships .env or backups')
ok('static\\profiles' in iss, 'installer keeps uploaded profile pictures out of the package')
ok('AppId={{' in iss and 'Compression=' in iss, 'installer has a stable AppId and compression')
ok('MediGenAIPro.exe' in iss and 'python --version' not in iss, 'installer packages the built exe and needs no Python')
ok('onlyifdoesntexist' in iss, 'installer keeps an existing .env on update')
ok('Source: "..\\dist\\MediGenAIPro\\*"' in iss, 'installer packages the built program folder')

help_txt = read('docs/HELP_CENTER.md')
for section in ['Getting started', 'Roles', 'Medicines and stock', 'Batches and expiry', 'Sales (POS)',
                'Returns', 'Prescriptions', 'Reports', 'Backups', 'Troubleshooting']:
    ok(section in help_txt, f'help center covers: {section}')
ok('python create_admin.py' in help_txt and 'Ctrl+F5' in help_txt, 'help center has the first-admin and refresh steps')

video = read('docs/VIDEO_SCRIPTS.md')
ok(video.count('## Video ') == 6, 'six video scripts')
ok('never show real' in video.lower(), 'video guide forbids showing real patient data')

removed = read('REMOVED_PHONE_CODE.md')   # v88.00: phone app removed on purpose
ok('mobile_' in removed and 'Android' in removed, 'removed phone code is documented in REMOVED_PHONE_CODE.md')

print(f"\nTOTAL: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
