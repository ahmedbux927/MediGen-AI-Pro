"""B4: the .env cleaner removes PowerShell lines, keeps settings, and never prints values. No MySQL."""
import importlib.util, os as _os, sys
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
RESULTS = []
def ok(c, msg): RESULTS.append((msg, bool(c)))

spec = importlib.util.spec_from_file_location('clean_env_copy', _os.path.join(ROOT, 'scripts', 'clean_env_copy.py'))
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

SAMPLE = """# settings
DB_NAME=pharmacy_management_system
DB_PASSWORD=fake-test-value
SECRET_KEY=fake-test-value-2
$dir = "C:\\MediGen"
Write-Host "starting"
if ($x) { exit }
[System.IO.File]::WriteAllText('a', 'b')

AI_ENABLED=1
"""
cleaned, removed, missing = M.clean_env(SAMPLE)
ok(removed == [5, 6, 7, 8], 'PowerShell lines are removed (4 lines, by line number)')
ok('DB_PASSWORD=fake-test-value' in cleaned and 'AI_ENABLED=1' in cleaned and '# settings' in cleaned,
   'settings, comments and blank lines are kept')
ok('$dir' not in cleaned and 'Write-Host' not in cleaned, 'no PowerShell text left in the cleaned file')
ok(missing == [], 'no required key reported missing when all three are set')

_, _, miss2 = M.clean_env('DB_NAME=x\n')
ok(set(miss2) == {'DB_PASSWORD', 'SECRET_KEY'}, 'missing DB_PASSWORD and SECRET_KEY are reported by name')
_, _, miss3 = M.clean_env('DB_NAME=x\nDB_PASSWORD=\nSECRET_KEY=y\n')
ok('DB_PASSWORD' in miss3, 'an empty required value counts as missing')

print('\n'.join(('PASS ' if c else 'FAIL ') + m for m, c in RESULTS))
