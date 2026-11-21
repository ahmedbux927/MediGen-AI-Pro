"""Stage 10 (Master Prompt v4): the Android companion.

Gradle project pinned (AGP 8.5.2, SDK 34/24/34, namespace com.medigen.aipro),
LAN-only server address validation with a plain-Java test, camera permission
for web barcode scanning, and honest docs: device checks are NOT RUN BY AGENT.
"""
import os as _os
import re
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


A = 'android'
ok(_os.path.exists(_os.path.join(ROOT, A, 'settings.gradle')), 'Gradle settings exist')
bg = read(f'{A}/build.gradle')
ok("8.5.2" in bg, 'AGP pinned at 8.5.2')
app_bg = read(f'{A}/app/build.gradle')
ok("namespace 'com.medigen.aipro'" in app_bg and 'compileSdk 34' in app_bg
   and 'minSdk 24' in app_bg and 'targetSdk 34' in app_bg, 'app module: namespace and SDK levels 34/24/34')

man = read(f'{A}/app/AndroidManifest.xml')
cfg = read('config.py')
mv = re.search(r'android:versionName="([^"]+)"', man).group(1)
cv = re.search(r"APP_VERSION\s*=\s*'([^']+)'", cfg).group(1)
ok(mv == cv, f'manifest versionName ({mv}) matches APP_VERSION ({cv})')
ok('android.permission.CAMERA' in man, 'manifest asks for the camera (web barcode scan)')

sa = read(f'{A}/app/src/com/medigen/aipro/ServerAddress.java')
ok('isLanHost' in sa and '192' in sa and '172' in sa and 'DEFAULT_PORT = 5000' in sa,
   'ServerAddress validates LAN ranges with default port 5000')
test = read(f'{A}/tests/ServerAddressTest.java')
ok('8.8.8.8' in test and 'expected' in test, 'ServerAddress test covers public-address rejection')
main = read(f'{A}/app/src/com/medigen/aipro/MainActivity.java')
ok('ServerAddress.normalize' in main, 'MainActivity uses the LAN validator')
ok('onPermissionRequest' in main and 'CookieManager' in main, 'camera permission bridge and cookie handling present')
ok('Server not reachable' in main, 'not-reachable state has a message and the setup (retry) screen')

ok('NOT RUN BY AGENT' in read(f'{A}/TEST_CHECKLIST.md'), 'TEST_CHECKLIST states plainly that device tests were not run')
ok('Never commit the keystore' in read(f'{A}/BUILD_APK.md'), 'BUILD_APK documents the signed release without committing the key')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
