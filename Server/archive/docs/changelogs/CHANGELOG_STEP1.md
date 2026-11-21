# MediGen AI Pro - Step 1 (cleanup)

## Removed
- Manufacturer feature: routes, pages, menu link, medicine form field, search, CSV column, chatbot entity.
- Database: `manufacturers` table and `medicines.manufacturer_id` (dropped automatically on first start).

## Changed (security and permissions)
- `config.py`: no fixed fallback SECRET_KEY. A random key is used when `.env` has none (logins reset on restart).
- Cashier can no longer receive payments (`/sales/<id>/pay`), per the role matrix.
- Customer delete is limited to Admin and Pharmacist.
- NaN and infinity are rejected in sale discounts, payments, medicine prices and purchase prices.
- Audit log now records: records clear, user add, delete, active toggle, access-time change.

## Breaking changes
- Medicine add/edit no longer asks for a manufacturer.
- Medicine CSV export has no Manufacturer column.
- Old manufacturer data is deleted by the migration. Make a backup before the first start.

## Tests
- New: tests/test_step1_cleanup.py (19 checks).
- Mock suite: all results the same as before Step 1, except the new suite. Two failures were already there before this step (profile tabs and profile-update audit).

## Not changed yet (waiting for decision)
- Dispensed prescriptions can still be edited. The tests expect this, the manual checklist says it must be locked.
- "In" stock adjustments do not update batches (needs an expiry decision).
- Raw database error text shown in flash messages (Step 10).
