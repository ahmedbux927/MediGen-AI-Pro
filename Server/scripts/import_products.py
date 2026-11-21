"""Import a product list (CSV or XLSX) into the medicines table. Backend only, no screen needed.

    python scripts/import_products.py FILE                 # dry run: shows what WOULD happen, writes nothing
    python scripts/import_products.py FILE --commit        # writes, only if every row is valid
    python scripts/import_products.py FILE --commit --update-existing
                                                           # also updates prices/details of matching items

Rules: nothing is written unless every row is valid (all-or-nothing). Existing stock is never changed.
A report CSV (line, action, errors, warnings) is written next to the file, or to --report.
Exit codes: 0 = OK (or dry run with no errors), 1 = rows have errors, 2 = could not read the file.
"""
import argparse
import csv
import os
import sys
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)

from pharmacy.services.product_import import read_file, build_plan, apply_plan  # noqa: E402


def existing_medicines(cur):
    cur.execute("SELECT medicine_id, name, barcode FROM medicines")
    rows = cur.fetchall()
    from pharmacy.services.product_import import name_key
    return {'barcodes': {r['barcode']: r for r in rows if r['barcode']},
            'names': {name_key(r['name']): r for r in rows}}


def write_report(path, plan):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['line', 'action', 'name', 'barcode', 'errors', 'warnings'])
        for it in plan:
            w.writerow([it['line'], it['action'], it['name'], it['barcode'] or '',
                        '; '.join(it['errors']), '; '.join(it['warnings'])])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('file')
    ap.add_argument('--commit', action='store_true', help='write to the database (default: dry run)')
    ap.add_argument('--update-existing', action='store_true', help='update matching items (never stock)')
    ap.add_argument('--report', help='report CSV path')
    ap.add_argument('--show', type=int, default=15, help='how many problem rows to print')
    args = ap.parse_args()

    try:
        with open(args.file, 'rb') as fh:
            data = fh.read()
        raw_rows, header_warnings = read_file(data, args.file)
    except (OSError, ValueError) as e:
        print('Could not read the file:', e)
        return 2

    import app as A                                   # the same database settings as the web app
    source = os.path.basename(args.file)
    with A.app.app_context():
        A.ensure_schema()
        cur = A.mysql.connection.cursor()
        try:
            plan, summary = build_plan(raw_rows, existing_medicines(cur), date.today(), args.update_existing)
            report = args.report or os.path.splitext(args.file)[0] + '_import_report.csv'
            write_report(report, plan)

            print(f"File: {args.file}  rows: {summary['rows']}")
            for w in header_warnings:
                print('  note:', w)
            c = summary['counts']
            print(f"  create {c['create']}  update {c['update']}  skip {c['skip']}  error {c['error']}")
            print('  unknown or missing: ' + ', '.join(f'{k} {v}' for k, v in summary['missing_fields'].items()))
            problems = [it for it in plan if it['errors']]
            for it in problems[:args.show]:
                print(f"  line {it['line']} ({it['name'] or 'no name'}): {'; '.join(it['errors'])}")
            if len(problems) > args.show:
                print(f'  ... {len(problems) - args.show} more, see {report}')
            print('  report:', report)

            if not args.commit:
                print('Dry run: nothing was written.' + (' Fix the errors first.' if problems else
                                                         ' Run again with --commit to write.'))
                return 1 if problems else 0
            if not summary['can_commit']:
                print('Not written: fix the error rows (or remove them) and run again.')
                return 1
            done = apply_plan(cur, plan, source, audit_fn=A.audit)
            A.mysql.connection.commit()
            print(f"Written: created {done['created']}, batches {done['batches']}, updated {done['updated']}, "
                  f"new categories {done['categories_added']}")
            return 0
        except Exception:
            A.mysql.connection.rollback()
            raise
        finally:
            cur.close()


if __name__ == '__main__':
    sys.exit(main())
