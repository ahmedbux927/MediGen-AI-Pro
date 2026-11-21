"""Sales report as a Word (.docx) file: the file opens, has the right table, summary and notes."""
import os as _os
ROOT = _os.environ.get('MEDIGEN_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))
import sys, io, re, unittest, zipfile
from datetime import date
from decimal import Decimal
sys.path.insert(0, ROOT)
from pharmacy.exports import build_docx


class DocxExportTest(unittest.TestCase):
    def setUp(self):
        self.headers = ['Date', 'Invoices', 'Net revenue (Rs.)']
        self.rows = [(date(2026, 10, 1), 3, Decimal('1250.50')), (date(2026, 10, 2), 0, 0.0)]
        self.data = build_docx('Sales report', self.headers, self.rows,
                               summary=[('Net revenue (Rs.)', 1250.5), ('Invoices', 3)],
                               notes=['Prepared from the sales records.'],
                               subtitle='Period: 2026-10-01 to 2026-10-02')
        from docx import Document
        self.doc = Document(io.BytesIO(self.data))

    def test_is_a_real_zip_docx(self):
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(self.data)))
        self.assertIn('word/document.xml', zipfile.ZipFile(io.BytesIO(self.data)).namelist())

    def test_table_has_header_and_rows(self):
        t = self.doc.tables[0]
        self.assertEqual([c.text for c in t.rows[0].cells], self.headers)
        self.assertEqual(len(t.rows), 1 + len(self.rows))
        self.assertEqual(t.rows[1].cells[0].text, '2026-10-01')
        self.assertEqual(t.rows[1].cells[2].text, '1250.5')

    def test_summary_and_notes_present(self):
        text = '\n'.join(p.text for p in self.doc.paragraphs)
        self.assertIn('Net revenue (Rs.): 1250.5', text)
        self.assertIn('Prepared from the sales records.', text)

    def test_empty_period_says_no_records(self):
        data = build_docx('Sales report', ['Date'], [])
        from docx import Document
        d = Document(io.BytesIO(data))
        self.assertIn('No records for this period.', d.tables[0].rows[1].cells[0].text)

    def test_report_page_offers_word_button(self):
        html = open(_os.path.join(ROOT, 'templates', 'reports.html'), encoding='utf-8').read()
        self.assertIn("rtype='sales'", html)
        self.assertRegex(html, r"fmt='docx'")

    def test_export_route_accepts_docx(self):
        src = open(_os.path.join(ROOT, 'pharmacy', 'routes', 'reports.py'), encoding='utf-8').read()
        self.assertIn("('csv', 'xlsx', 'pdf', 'docx')", src)
        self.assertIn('wordprocessingml.document', src)


if __name__ == '__main__':
    import unittest as _u
    suite = _u.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = _u.TextTestRunner(stream=open(_os.devnull, 'w')).run(suite)
    for t, _tb in res.failures + res.errors:
        print('FAIL', t.id())
    for _ in range(res.testsRun - len(res.failures) - len(res.errors)):
        print('PASS')
    sys.exit(0 if res.wasSuccessful() else 1)
