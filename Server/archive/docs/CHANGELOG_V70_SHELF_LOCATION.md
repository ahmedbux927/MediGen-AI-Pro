# MediGen v70 - Shelf location per medicine (Phase 2)

## What changed
- Medicine **Add** and **Edit** forms have a new "Shelf Location" field (optional, max 40 characters, example `A-3`).
- Medicines list shows the shelf under the category, e.g. `Tablet · A-3`, so staff can find the item quickly.
- Edit button passes the shelf value to the edit window (quotes escaped).

## Backend
- `pharmacy/lib.py` `_read_medicine_form`: reads `rack_location`, trims it, stores NULL when empty, rejects values longer than 40 characters.
- `pharmacy/repos/medicines.py`: `insert_medicine` and `update_medicine` save `rack_location`.
- No new database column. `medicines.rack_location` (VARCHAR(40)) already exists and is created by the existing schema check. The AI agent's `set_shelf_location` tool uses the same column.

## Tests
- New `tests/test_shelf_location.py` (6 checks: trim, empty→NULL, 40/41 length limit, insert and update SQL).
- Updated two assertions that depended on the old argument order (`test_barcode_step7.py`, `test_repos.py`).
- `tests/run_all.py`: 1347 passed, 0 failed.
- Freeze manifest regenerated (`tests/test_backend_freeze.py --write`).

## Not changed
- No static asset changes, so no service worker bump. Browser cache is not affected.

## Run / check on the shop PC
1. Copy the v70 folder over the current project (keep your `.env` and `logs` folder).
2. Restart the server.
3. Open Medicines → Add New Medicine → fill "Shelf Location" → Save. The list should show `· A-3` under the category.
4. Edit an existing medicine → the shelf field should be filled from the saved value.
