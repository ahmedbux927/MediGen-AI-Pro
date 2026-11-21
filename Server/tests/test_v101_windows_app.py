"""v101.02: the Windows app build is complete and self-consistent.

The exe runs the Settings backup/restore scripts through its own --script
mode (there is no loose Python inside a PyInstaller build), build_exe.bat
ships the scripts folder next to the exe, MAKE_WINDOWS_APP.bat drives the
whole build, and the installer README matches what MediGen.iss really does.
"""
import os as _os
import sys

ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

RESULTS = []


def ok(c, msg):
    RESULTS.append((msg, bool(c)))


def read(rel):
    with open(_os.path.join(ROOT, rel), encoding='utf-8', errors='ignore') as f:
        return f.read()


desktop = read('desktop.py')
ok("'--script'" in desktop and 'runpy.run_path' in desktop, 'the exe can run a bundled script via --script (frozen backup fix)')
settings = read('pharmacy/routes/settings.py')
ok('_script_cmd' in settings and "getattr(sys, 'frozen', False)" in settings, 'settings routes use the frozen-aware script command')
ok(settings.count('subprocess.run(_script_cmd(script)') == 2, 'both backup-now and restore-test use it')

build = read('build_exe.bat')
ok('"scripts"' in build and 'dist\\MediGenAIPro\\scripts' in build, 'build_exe.bat copies the scripts folder next to the exe')
ok('MAKE_WINDOWS_APP' not in build, 'build_exe.bat stays the single-purpose exe builder')

maker = read('MAKE_WINDOWS_APP.bat')
ok('call build_exe.bat' in maker and 'MediGen.iss' in maker and 'Inno Setup 6' in maker,
   'MAKE_WINDOWS_APP.bat builds the exe, then the Setup file, and explains a missing Inno Setup')

iss = read('installer/MediGen.iss')
readme = read('installer/README.md')
ok('MediGenAIPro.exe' in iss and 'onlyifdoesntexist' in iss, 'installer ships the built exe and never overwrites .env')
ok('start_medigen.bat' not in readme and 'MediGenAIPro.exe' in readme, 'installer README describes the exe installer (not the old source installer)')
ok('mysql' in readme.lower() and 'portable' in readme.lower(), 'installer README documents the portable MySQL option')

for msg, c in RESULTS:
    print(('PASS ' if c else 'FAIL ') + msg)
sys.exit(0 if all(c for _, c in RESULTS) else 1)
