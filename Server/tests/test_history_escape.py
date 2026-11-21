"""Stock history table must escape free-text fields before writing them into the page (stored XSS guard)."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StockHistoryEscapeTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, 'templates', 'medicines.html'), encoding='utf-8') as f:
            self.src = f.read()
        m = re.search(r"data\.forEach\(function\(r\) \{(.*?)html \+= '</tbody></table>';", self.src, re.S)
        self.assertIsNotNone(m, 'history rendering block not found')
        self.block = m.group(1)

    def test_note_reason_and_user_are_escaped(self):
        for field in ('r.note', 'r.reason', 'r.by', 'r.when'):
            self.assertIn('e(' + field + ')', self.block, field + ' must go through e()')

    def test_no_raw_free_text_concatenated(self):
        for field in ('r.note', 'r.by', 'r.reason'):
            self.assertNotRegex(self.block, r"\+\s*" + re.escape(field) + r"\s*[+)]", field + ' written without escaping')

    def test_escape_helper_defined(self):
        self.assertIn('var e = function', self.src)
        self.assertIn("replace(/&/g, '&amp;')", self.src)


if __name__ == '__main__':
    # print one PASS line per passing test so tests/run_all.py counts them
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(stream=open(os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
