"""Every static file a template links to must exist in the project (no broken styles or scripts)."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import re, glob, sys, unittest


def _template_static_refs():
    refs = []
    for f in glob.glob(_os.path.join(ROOT, 'templates', '**', '*.html'), recursive=True):
        text = open(f, encoding='utf-8').read()
        for m in re.finditer(r"url_for\(\s*'static',\s*filename='([^']+)'", text):
            refs.append((_os.path.relpath(f, ROOT), m.group(1)))
    return refs


class StaticRefsTest(unittest.TestCase):
    def test_templates_are_found(self):
        self.assertGreaterEqual(len(_template_static_refs()), 5)

    def test_every_static_file_exists(self):
        missing = [(f, p) for f, p in _template_static_refs()
                   if not _os.path.exists(_os.path.join(ROOT, 'static', p.split('?')[0]))]
        self.assertEqual(missing, [], 'missing static files: %s' % missing)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
