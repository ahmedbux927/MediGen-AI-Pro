# MediGen AI Pro - Step 6 (English / Roman Urdu), part 1

## What changed
- **Language switch** in the top bar: button "Roman Urdu" (or "English" when Roman Urdu is on).
  - English is the default. Roman Urdu is shown only when the user chooses it.
  - The choice is saved in the user's session, so it stays while they work.
- **Sidebar labels** come from one file: `pharmacy/i18n.py` (English and Roman Urdu for each label).
  - Examples: Medicines / Dawaiyan, New Sale / Nayi Sale, Daily Closing / Roz ka Hisaab, Customer Dues / Udhaar.
  - Adding or changing a label means editing this one file, not every template.
- `/language` route (POST only, CSRF protected). It refuses unknown languages and only redirects back to this site.

## Tests
- Full mock suite: 473 pass, 2 fail (the 2 old profile tests, unchanged).
- `tests/test_i18n_step6.py` (new, 18 checks): every label has both languages, fallback to English, language
  values cleaned, switch button shows and carries the token, choice saved, sidebar changes, unknown value refused,
  no redirect to another website, switch without token refused.
- URL map: 67 routes (1 new: `/language`).

## Pharmacy benefit
- Staff who are more comfortable in Roman Urdu can use the menu in it; English stays for everyone else.

## Not done yet (Step 6 part 2)
- Page titles, headings, buttons and table headers on each page (only the sidebar is translated now).
- Flash messages (the small messages after saving) are still English.
- The greeting ("Good morning") is still English.
- Customers page: hide medical history from Cashier; Medicines page: hide cost price from Cashier (open audit items).

## Files to put in the project
- Replace: `templates/base.html`, `pharmacy/lib.py`, `pharmacy/routes/__init__.py`.
- New: `pharmacy/i18n.py`, `pharmacy/routes/language.py`, `tests/test_i18n_step6.py`, `CHANGELOG_STEP6.md`.
- Everything else stays the same.
