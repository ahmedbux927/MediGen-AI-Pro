# Step 22 - Numbered schema migrations (backend track, B2, v49.2)

## Added
- `pharmacy/services/migrations.py`: runs `database/migrations/NNN_name.sql` files in number order.
  Each file runs once; the number is stored in the `schema_version` table. A failing file stops the run
  and is not recorded as applied. Two files with the same number are refused.
- `database/migrations/002_sale_guard.sql`: the `sale_guard` table (moved here from the B1 code).
- `tests/test_migrations.py`: 13 checks (file rules, order, run once, stop on error, project file).

## Changed
- `pharmacy/core.py` `ensure_schema()`: calls `run_migrations(cur)` at startup.

## Not changed (on purpose)
- Column changes stay in the existing startup checks in `ensure_schema()`. MySQL 8 has no
  `ADD COLUMN IF NOT EXISTS`, so they are not safe as plain migration files yet. Move them over one at a time,
  after each is tested on a copy of the shop database.
- Templates and static files (freeze test passes).

## Tests
- Result: 1165 passed, 0 failed (mock database).

## Not tested here
- Real MySQL: run `python tests\run_all.py --live` on the shop PC. On the check database, confirm
  `SELECT * FROM schema_version;` shows version 2 (sale_guard) after the first start.
