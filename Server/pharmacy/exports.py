"""Report files: Excel (.xlsx) and PDF (Sprint 2). Pure functions, no database and no Flask.

Both take the same input: a title, column headers, rows, and an optional summary (list of (label, value))
and notes (list of text lines for the bottom of the page)."""
from datetime import date, datetime
from decimal import Decimal
import io


def to_cell(value):
    """Turn database values into something Excel and PDF can show."""
    if value is None:
        return ''
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M')
    if isinstance(value, date):
        return value.isoformat()
    return value


def build_xlsx(title, headers, rows, summary=None, notes=None):
    """Return the bytes of an .xlsx file."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = 'Report'[:31]
    ws['A1'] = title
    ws['A1'].font = Font(bold=True, size=14)
    header_row = 3
    for col, head in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=head)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='0F9AA0')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for r_index, row in enumerate(rows, start=header_row + 1):
        for c_index, value in enumerate(row, start=1):
            cell = ws.cell(row=r_index, column=c_index, value=to_cell(value))
            if isinstance(cell.value, float):
                cell.number_format = '#,##0.00'
    last = header_row + len(rows)
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{max(last, header_row)}"

    row_at = last + 2
    if summary:
        ws.cell(row=row_at, column=1, value='Summary').font = Font(bold=True)
        row_at += 1
        for label, value in summary:
            ws.cell(row=row_at, column=1, value=label)
            cell = ws.cell(row=row_at, column=2, value=to_cell(value))
            if isinstance(cell.value, float):
                cell.number_format = '#,##0.00'
            row_at += 1
    if notes:
        row_at += 1
        for line in notes:
            ws.cell(row=row_at, column=1, value=line).font = Font(italic=True, color='44546F')
            row_at += 1

    for col in range(1, len(headers) + 1):
        width = max(len(str(ws.cell(row=r, column=col).value or '')) for r in range(header_row, last + 1))
        ws.column_dimensions[get_column_letter(col)].width = min(max(12, width + 2), 40)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_pdf(title, headers, rows, summary=None, notes=None, subtitle=None):
    """Return the bytes of a PDF file (A4, landscape when there are many columns)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    page = landscape(A4) if len(headers) > 5 else A4
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=page, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36,
                            title=title)
    styles = getSampleStyleSheet()
    story = [Paragraph(_esc(title), styles['Title'])]
    if subtitle:
        story.append(Paragraph(_esc(subtitle), styles['Normal']))
    story.append(Spacer(1, 12))

    data = [[_esc(h) for h in headers]]
    for row in rows:
        data.append([_esc(_pdf_text(v)) for v in row])
    if len(data) == 1:
        data.append(['No data for this period'] + [''] * (len(headers) - 1))
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F9AA0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F7FB')]),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#DBE4F0')),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(table)

    if summary:
        story.append(Spacer(1, 14))
        story.append(Paragraph('<b>Summary</b>', styles['Normal']))
        for label, value in summary:
            story.append(Paragraph(f"{_esc(label)}: <b>{_esc(_pdf_text(value))}</b>", styles['Normal']))
    if notes:
        story.append(Spacer(1, 10))
        for line in notes:
            story.append(Paragraph(f"<i>{_esc(line)}</i>", styles['Normal']))
    doc.build(story)
    return buf.getvalue()


def _pdf_text(value):
    value = to_cell(value)
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def _esc(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_docx(title, headers, rows, summary=None, notes=None, subtitle=None):
    """Word (.docx) report: title, period line, summary figures, a table with a shaded header row, notes.
    Needs the python-docx package (listed in requirements.txt)."""
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    doc = Document()
    doc.styles['Normal'].font.size = Pt(10)
    doc.add_heading(title, level=1)
    if subtitle:
        doc.add_paragraph(subtitle)
    if summary:
        doc.add_heading('Summary', level=2)
        for label, value in summary:
            p = doc.add_paragraph()
            p.add_run(f'{label}: ').bold = True
            p.add_run(str(to_cell(value)))

    doc.add_heading('Details', level=2)
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ''
        run = cell.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade = OxmlElement('w:shd')
        shade.set(qn('w:val'), 'clear')
        shade.set(qn('w:color'), 'auto')
        shade.set(qn('w:fill'), '0F9AA0')
        cell._tc.get_or_add_tcPr().append(shade)
    # repeat the header row on every printed page
    trPr = table.rows[0]._tr.get_or_add_trPr()
    repeat = OxmlElement('w:tblHeader')
    repeat.set(qn('w:val'), 'true')
    trPr.append(repeat)

    if not rows:
        table.add_row().cells[0].text = 'No records for this period.'
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = '' if value is None else str(to_cell(value))

    if notes:
        doc.add_heading('Notes', level=2)
        for line in notes:
            doc.add_paragraph(line)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
