"""Stock count from the command line (Phase 3). Every command needs --by USERNAME (an active app user).

  python scripts/stock_count.py start --by ahmed --note "Monthly count"
  python scripts/stock_count.py show 7
  python scripts/stock_count.py count 7 --barcode 2900000000001 --qty 152 --by ahmed
  python scripts/stock_count.py count 7 --medicine 12 --qty 0 --by ahmed
  python scripts/stock_count.py submit 7 --by ahmed
  python scripts/stock_count.py approve 7 --by admin          (Admin only; changes stock)
  python scripts/stock_count.py cancel 7 --by ahmed

Exit codes: 0 = done, 1 = refused (the message says why), 2 = bad input or user not found.
"""
import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, ROOT)
from pharmacy.services import stock_count as SC  # noqa: E402


def find_user(cur, username):
    cur.execute("""SELECT u.user_id, r.role_name FROM users u JOIN roles r ON r.role_id = u.role_id
                   WHERE u.username=%s AND u.is_active=1""", (username,))
    return cur.fetchone()


def show(cur, count_id):
    cur.execute("SELECT count_id, status, started_at, note FROM stock_counts WHERE count_id=%s", (count_id,))
    head = cur.fetchone()
    if not head:
        print('No such count.'); return 2
    cur.execute("""SELECT l.medicine_id, m.name, m.barcode, l.system_qty, l.counted_qty, m.price, m.cost_price
                   FROM stock_count_lines l JOIN medicines m ON m.medicine_id = l.medicine_id
                   WHERE l.count_id=%s ORDER BY m.name""", (count_id,))
    lines = cur.fetchall()
    cost = {r['medicine_id']: r['cost_price'] for r in lines}
    s = SC.summarise(lines, cost)
    print(f"Count #{head['count_id']}  status: {head['status']}  started: {head['started_at']}  {head['note'] or ''}")
    print(f"lines {s['lines']}  counted {s['counted']}  not counted {s['uncounted']}  changed {s['changed']}  "
          f"short {s['short_units']}  over {s['over_units']}  value change {s['value_change']:,.2f}")
    pending = [r for r in lines if r['counted_qty'] is None]
    for r in pending[:30]:
        print(f"  not counted: {r['name']} (system {r['system_qty']})")
    if len(pending) > 30:
        print(f'  ... and {len(pending) - 30} more')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('start'); p.add_argument('--by', required=True); p.add_argument('--note', default='')
    p = sub.add_parser('show'); p.add_argument('count_id', type=int)
    p = sub.add_parser('count'); p.add_argument('count_id', type=int); p.add_argument('--qty', type=int, required=True)
    g = p.add_mutually_exclusive_group(required=True); g.add_argument('--barcode'); g.add_argument('--medicine', type=int)
    p.add_argument('--by', required=True)
    for name in ('submit', 'cancel', 'approve'):
        p = sub.add_parser(name); p.add_argument('count_id', type=int); p.add_argument('--by', required=True)
    args = ap.parse_args()

    import app as A
    with A.app.app_context():
        db = A.mysql.connection
        cur = db.cursor()
        try:
            if args.cmd == 'show':
                return show(cur, args.count_id)
            user = find_user(cur, args.by)
            if not user:
                print(f"No active user named '{args.by}'."); return 2
            if args.cmd == 'start':
                count_id = SC.start_count(cur, user['user_id'], args.note)
                msg = f'Count #{count_id} started. Count every medicine, then submit.'
            elif args.cmd == 'count':
                medicine_id = args.medicine
                if args.barcode:
                    cur.execute("SELECT medicine_id FROM medicines WHERE barcode=%s", (args.barcode,))
                    row = cur.fetchone()
                    if not row:
                        print('No medicine has that barcode.'); return 2
                    medicine_id = row['medicine_id']
                SC.record_count(cur, args.count_id, medicine_id, args.qty, user['user_id'])
                msg = 'Count recorded.'
            elif args.cmd == 'submit':
                SC.submit_count(cur, args.count_id)
                msg = 'Count submitted. An Admin can approve it now.'
            elif args.cmd == 'cancel':
                SC.cancel_count(cur, args.count_id)
                msg = 'Count cancelled. No stock was changed.'
            elif args.cmd == 'approve':
                changed = SC.approve_count(cur, args.count_id, user['user_id'], user['role_name'], A.audit)
                msg = f'Count approved. {changed} medicine(s) updated.'
            db.commit()
            print(msg)
            return 0
        except SC.CountError as e:
            db.rollback()
            print('Refused:', e)
            return 1
        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()


if __name__ == '__main__':
    sys.exit(main())
