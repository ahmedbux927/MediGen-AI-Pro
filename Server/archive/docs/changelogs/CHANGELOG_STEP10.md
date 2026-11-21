# MediGen AI Pro - Step 10 (Security and Cashier privacy), part 1

## What changed
- **Safe error messages.** Pages no longer show technical errors such as database text.
  - The user sees a short message, for example "Backup failed. Please try again."
  - The full error goes only to the server log (terminal).
  - 37 places in 14 route files now use the one helper `flash_unexpected()` in `pharmacy/lib.py`.
  - Validation messages (wrong input) still show their own clear text, as before.
- **Logout only by button.** `/logout` now accepts POST only, with the CSRF token.
  - A plain link or a typed address can no longer log a user out (GET gives 405).
  - Sidebar "Logout" is now a small form button; it looks the same as before.
- **Cashier privacy (display).**
  - Medicines page: cost price and margin are hidden for Cashier. The edit window does not receive the cost either.
  - Customers page: "Medical History" column and "With History" stat are hidden for Cashier.
  - Prescription page: the medical history stored in the dropdown is empty for Cashier.
  - Admin and Pharmacist see everything as before.

## Files
- Replace: `pharmacy/lib.py`, `pharmacy/core.py` (unchanged content, included for safety), `pharmacy/routes/*.py` (14 files), `templates/base.html`, `templates/medicines.html`, `templates/customers.html`, `templates/add_prescription.html`
- New: `tests/test_step10_security.py` (11 checks)

## Tests
- Full mock suite: 507 pass, 2 fail (the 2 old profile tests, unchanged).
- Step 10 checks: no raw error text in routes, safe message content, GET /logout = 405, wrong token refused, right token logs out, Cashier hides medical history, Admin still sees it, cost hidden from Cashier.

## Pharmacy benefit
- A cashier cannot see what the shop paid for a medicine, or a customer's health history, even by accident on screen.
- Staff cannot be logged out by accident from a link; the owner's login is safer.
- Errors are short and clear at the counter; the technical detail stays with the owner's computer log.

## Not done yet (planned for later parts)
- Content-Security-Policy header: the current pages use inline scripts and styles, so a strict policy would break them. It needs a planned clean-up first.
- Photo upload: extension is checked, but no file size limit and no image content check yet.
- CSV exports and API responses: hiding is on the screen only. Server-side filtering for Cashier is still to be added.
- Profile page tests (2 old failures).
