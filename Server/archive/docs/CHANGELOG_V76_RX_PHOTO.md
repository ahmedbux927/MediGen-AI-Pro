# MediGen v76 - Prescription from photo (Phase 4, assisted intake; includes v72-v75)

## What changed
- **New page: Prescriptions → Start from a photo** (`/prescriptions/scan`). Also linked from the Add Prescription page.
  1. Choose the patient and upload a photo (JPG, PNG or WEBP, up to 5 MB; the phone camera opens directly).
  2. The system tries to read the text (OCR, if an engine is installed) and matches medicine names to the medicine list.
  3. The **review page** shows the photo and one editable row per suggestion: medicine, dosage text copied from the paper, days.
  4. Rows are marked **matched**, **check name** (close spelling) or **not matched**.
  5. The pharmacist types the doctor name, ticks **"I checked every medicine, dosage and day against the paper"**, and saves.
  6. Without the tick, nothing is saved.
- **Cancel** deletes the photo immediately.
- Photos are kept only in a private temp folder (`instance/rx_tmp`), with random names, served only to Admin/Pharmacist with `no-store`, and deleted after save, cancel, or one hour.
- Without an OCR engine (the default) the review page opens empty, and staff type the rows. Nothing breaks.

## Safety rules built in
- A photo is a source of suggestions only. The system never diagnoses, never chooses a dose, and never adds a row by itself.
- The dosage text is copied from the photo; staff check it.
- Only Admin and Pharmacist can use the pages (all 4 routes).
- The save writes the audit line `prescription.scan_add`.
- Allergy warnings from the existing check still run after the save.

## Files
- `pharmacy/services/rx_scan.py` (new): file type check from the bytes, temp storage, cleanup, OCR plug-in (Tesseract if `tesseract` is installed; no network calls), medicine matching.
- `pharmacy/routes/rx_scan.py` (new): upload, image, save, cancel.
- `templates/rx_scan.html`, `templates/rx_review.html` (new), `templates/add_prescription.html` (link).
- `pharmacy/routes/__init__.py`: registers the routes.
- `.gitignore`: `instance/` added.
- `tests/test_rx_scan.py` (new, 33 checks).

## Tests
- `tests/run_all.py`: 1451 passed, 0 failed. Freeze manifest regenerated.
- Templates parse (Jinja syntax checked).
- Not verified in a browser or with a real OCR engine. Real prescriptions vary a lot; the matching is a helper, not a reader.

## Limits (please read)
- Accuracy depends on the OCR engine and photo quality. Handwriting is usually unreadable for Tesseract.
- Medicine matching is by name only (no strength or salt check yet).
- The OCR option is not turned on by default. To use Tesseract: install it on the PC so that `tesseract` runs from the command line.

## Check on the shop PC
1. Copy v76 over the project (keep `.env` and `logs`), restart, Ctrl+F5. Do not copy the `instance` folder.
2. Prescriptions → Add Prescription → "Start from a photo". Choose a customer and a clear printed prescription photo.
3. Without OCR: the review is empty. Add rows by hand, enter the doctor name, tick the box, save.
4. Try saving without the tick: it must refuse. Try Cancel: the photo must be deleted.
