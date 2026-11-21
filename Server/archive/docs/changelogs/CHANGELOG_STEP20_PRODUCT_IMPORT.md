# Step 20 - Product import, backup restore helper, frontend freeze (backend track, v49)

## Added
- `pharmacy/services/product_import.py`: reads CSV/XLSX product lists, checks every row (prices, barcode, dates,
  whole numbers, placeholders), builds a plan (create / update / skip / error), and writes it in one transaction.
  - Rules: all-or-nothing; placeholders ("Verify...", "N/A") become NULL; Rx "Yes"/"No" only, unclear = NULL;
    existing stock is never changed by import; every new medicine gets an audit row.
- `scripts/import_products.py`: dry run by default; `--commit` writes; `--update-existing`; writes a report CSV.
- `scripts/docx_products_to_csv.py`: converts the 230-product Word master list to CSV.
- `database/samples/`: the 230-product docx and the converted CSV (demo data, not verified stock).
- `scripts/restore_backup.py`: restores a Workbench backup folder into a NEW check database (never the live one).
- `docs/RESTORE_AND_IMPORT_STEPS.md`: step-by-step guide in Roman Urdu.
- `tests/test_product_import.py`, `tests/test_restore_backup.py`: 44 + 6 checks, no MySQL needed.
- `tests/test_backend_freeze.py` + `tests/frontend_manifest.json`: fails if any template or static file changes.

## Changed
- `pharmacy/core.py` `ensure_schema()`: adds product columns to `medicines` when missing (product_code, generic_name,
  manufacturer, strength, dosage_form, pack_size, rack_location, rx_required, schedule, tax_rate, import_source),
  and tries a unique index on `barcode` (logs a warning if old data has duplicates).

## Not changed
- templates/ and static/ (checked by the freeze test). No route, URL or JSON shape changed.

## Not tested here
- Real MySQL: this environment has no MySQL server. Run `python tests\run_all.py --live` on the shop PC, and the
  restore steps in docs/RESTORE_AND_IMPORT_STEPS.md against the check database first.
