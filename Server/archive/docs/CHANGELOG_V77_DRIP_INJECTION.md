# MediGen v77 - Drip and injection record (Phase 4; includes v72-v76)

## What changed
- New sidebar page **Drip & Injection** (Admin and Pharmacist).
  - Choose patient, medicine (only drip and injection medicines are listed), how it was given (IV drip, IV injection, IM injection, SC injection), dose text, quantity (1 to 50), and optional notes.
  - Saving takes the quantity out of stock (oldest expiry first) and writes a stock history line "Given to patient".
  - Below the form: today's records with time, patient, medicine, route, dose, quantity and who gave it.
- **Medicine add and edit forms** have a new **Dosage Form** list: Tablet, Capsule, Syrup, Suspension, Cream, Ointment, Drops, Injection, Drip / IV fluid, Inhaler, Other. Only Injection and Drip / IV fluid medicines appear on the drip page.

## Safety rules
- A medicine that is not an injection or drip is refused on this page (use a normal sale instead).
- Stock is checked before it is taken. If stock is too low, nothing is saved.
- The medicine row is locked while saving, so two users cannot take the same stock at once.
- One save either writes everything (stock, stock history, record, audit line) or nothing.
- The system does not check the dose or the doctor's order. The staff member types the dose from the order.

## Files
- `pharmacy/services/drip_record.py` (new): form rules, drip form check, table creation.
- `pharmacy/routes/drip.py` (new): `/drip` page and `/drip/add` save.
- `templates/drip.html` (new), `templates/base.html` (sidebar link), `templates/medicines.html` (Dosage Form field).
- `pharmacy/lib.py`: `MEDICINE_FORMS` list, dosage form read and checked in `_read_medicine_form`.
- `pharmacy/repos/medicines.py`: insert and update save `dosage_form`.
- `tests/test_drip_record.py` (new, 26 checks). Updated older checks for the new medicine form field (`test_barcode_step7.py`, `test_repos.py`, `test_shelf_location.py`).

## Tests
- `tests/run_all.py`: 1480 passed, 0 failed. Freeze manifest regenerated.
- Templates parse (Jinja syntax checked).
- Not verified in a browser or against live MySQL.

## Limits
- Records are not linked to a prescription yet.
- Existing medicines have no dosage form until staff set it (Medicines → Edit). Until then they do not show on the drip page.
- A record cannot be edited or deleted from the page (for audit). A mistake needs a correction through stock adjust.

## Check on the shop PC
1. Copy v77 over the project (keep `.env` and `logs`), restart, Ctrl+F5. The new table is created on first open.
2. Medicines → edit an injection medicine → Dosage Form: Injection → Save.
3. Drip & Injection → choose patient, medicine, route, dose "1 vial 2 ml", quantity 1 → Record. Stock should go down by 1 and the row should appear under "Given today".
4. Try a tablet on this page: it must be refused.
