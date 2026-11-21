# MediGen AI Pro - Step 6 part 2 (first part): Roman Urdu page labels

## Done
- Greeting ("Good morning" / "Good afternoon" / "Good evening" and "Welcome back") now follows the language switch.
- Dashboard: welcome text, stat cards, chart and alert headings, quick action labels.
- Medicines page: title, subtitle, Add Medicine button, search placeholder, table headers.
- Customers page: title, subtitle, stat labels, Add New Customer button, search placeholder, table headers.
- `pharmacy/i18n.py`: about 60 new English / Roman Urdu pairs.

## Not done yet (next part)
- Flash messages (small messages after saving) are still English.
- Other pages: Sales, New Sale, Purchases, Prescriptions, Batches, Reports, Users, Settings, Profile, modal dialogs and form fields.

## Already done before this step
- Cashier does not see cost price (Medicines page and CSV) or medical history (Customers page).

## Test
- `tests/test_step6b_labels.py` (9 checks). Full suite: 508 passed, 0 failed.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5. Click the "Roman Urdu" button in the top bar to switch.
