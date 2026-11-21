# MediGen AI Pro - Step 3 (data layer, part 1)

## What changed
- New folder `pharmacy/repos/`: plain SQL functions that take a cursor. No Flask code in this folder.
  - `repos/medicines.py`: medicine list and paging, stats, duplicate-name check, insert, update, FIFO batch removal, stock adjustment rows, stock history, delete, CSV export rows, category list.
  - `repos/catalog.py`: categories, customers, suppliers (list, add, delete, category usage check).
- `pharmacy/routes/medicines.py` and `pharmacy/routes/catalog.py` now call these functions. They have no raw SQL any more.
- SQL text is unchanged, so the database work is the same as before.
- Routes still decide commit and rollback. Flash messages, redirects and role checks are unchanged.
- Small change: the medicine list now checks the filter name once, and the stock history limit (15) is a query parameter.

## Not moved yet (still SQL inside routes)
- Sales, purchase, batches, prescriptions, users, audit, reports, profile, records, backup.
- These follow in the next step (Step 3 part 2), so each area moves with its own tests.

## Tests
- Full mock suite: 376 pass, 2 fail. The 2 failures are the old profile ones (same as Step 2).
- New `tests/test_repos.py` (27 checks): paging and clamping, filters, FIFO batch order, lock clauses, duplicate-name rule when editing, insert order, NULL-safe stats, and a check that the two route files have no raw SQL.
- URL map: 64 routes, identical to the single-file version.

## Files to put in the project
- Replace: `pharmacy/routes/medicines.py`, `pharmacy/routes/catalog.py`.
- New folder: `pharmacy/repos/` (copy the whole folder).
- New test: `tests/test_repos.py`.
- Everything else stays the same.
