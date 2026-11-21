"""Barcode label sheet (Stage 12, Master Prompt v4).

Builds an A4 PDF of shelf labels (3 across x 8 down) with a real Code 128
barcode for every item, drawn by reportlab (already a project dependency).
Only items that HAVE a barcode can be labelled - a printed code the till
cannot match would be worse than no label.
"""
import io

COLS, ROWS = 3, 8
PAGE_W, PAGE_H = 595.0, 842.0          # A4 in points
MARGIN = 28.0
CELL_W = (PAGE_W - 2 * MARGIN) / COLS
CELL_H = (PAGE_H - 2 * MARGIN) / ROWS


def build_labels_pdf(items):
    """items: list of dicts {name, barcode, price, copies}. Returns PDF bytes."""
    from reportlab.graphics.barcode.code128 import Code128
    from reportlab.pdfgen import canvas

    labels = []
    for it in items:
        code = (it.get('barcode') or '').strip()
        if not code:
            continue
        for _ in range(max(1, min(50, int(it.get('copies') or 1)))):
            labels.append(it)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    if not labels:
        c.setFont('Helvetica', 11)
        c.drawString(MARGIN, PAGE_H - 60, 'No labels to print. Choose items that have a barcode.')
        c.showPage()
        c.save()
        return buf.getvalue()
    for idx, it in enumerate(labels):
        pos = idx % (COLS * ROWS)
        if idx and pos == 0:
            c.showPage()
        col, row = pos % COLS, pos // COLS
        x = MARGIN + col * CELL_W
        y_top = PAGE_H - MARGIN - row * CELL_H
        # item name
        c.setFont('Helvetica-Bold', 8)
        name = (it.get('name') or '')[:34]
        c.drawCentredString(x + CELL_W / 2, y_top - 12, name)
        # barcode
        bc = Code128(str(it['barcode']), barHeight=30, barWidth=0.9, humanReadable=False)
        bx = x + max(4, (CELL_W - bc.width) / 2)
        bc.drawOn(c, bx, y_top - 48)
        # code + price under the bars
        c.setFont('Helvetica', 7.5)
        c.drawCentredString(x + CELL_W / 2, y_top - 58, str(it['barcode']))
        price = it.get('price')
        if price is not None:
            c.setFont('Helvetica-Bold', 9)
            c.drawCentredString(x + CELL_W / 2, y_top - 70, f"Rs. {float(price):,.0f}")
    c.showPage()
    c.save()
    return buf.getvalue()
