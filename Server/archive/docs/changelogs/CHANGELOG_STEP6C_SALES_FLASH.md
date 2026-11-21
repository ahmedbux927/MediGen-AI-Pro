# MediGen AI Pro - Step 6 part 2 (second part): Sales, New Sale and flash messages

## Done
- Sales Records page: title, subtitle, stat labels, Create New Sale, Search button, table headers.
- Create New Sale page: title, subtitle, customer and payment labels, barcode placeholder, table headers, Add Another Item, discount, payment received, Complete Sale, Add New Customer dialog title.
- Flash messages (small messages after saving or errors): 69 fixed messages now show in Roman Urdu when Roman Urdu is selected (`FLASH_UR` in `pharmacy/i18n.py`).
- Messages that include a number or a name (for example "Medicine 5 deleted", "Insufficient stock for ...") stay in English. They can be added one by one later.

## Not done yet
- Purchases, Prescriptions, Batches, Categories, Suppliers, Reports, Users, Settings, Profile, Daily Closing, Customer Dues pages.
- Modal dialogs and form fields on those pages.
- Flash messages with numbers or names.

## Test
- `tests/test_step6b_labels.py` (14 checks). Full suite: 513 passed, 0 failed.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5. Use the "Roman Urdu" button in the top bar.
