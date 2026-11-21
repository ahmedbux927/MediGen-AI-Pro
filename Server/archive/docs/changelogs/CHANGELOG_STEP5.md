# MediGen AI Pro - Step 5 (business features)

## What changed
- **Daily Closing** at `/daily-closing` (Admin, Pharmacist).
  - Pick any date (default today; a bad date shows today).
  - Shows: number of bills, units sold, sales total, new customer dues created that day.
  - Money received by Cash, Card, Online (sale-time payments plus customer dues payments on that day).
  - Refunds given that day, and the net (received minus refunds).
  - Print button for the end-of-day paper.
- **Customer Dues** at `/customer-dues` (Admin, Pharmacist).
  - Customers who still owe money, biggest debt first, with total due and oldest sale date.
  - WhatsApp button opens WhatsApp with a Roman Urdu / English reminder filled in (first name, shop name, amount). The staff member presses Send.
  - Pakistani mobile numbers are converted automatically: 0300-1234567, +92 300 1234567, 3001234567 all become 923001234567.
  - Customers without a valid mobile show "No valid mobile number" instead of a broken button.
  - Walk-in sales (no customer) are not listed, because there is no one to remind.
- Nav: two new links under Transactions ("Daily Closing", "Customer Dues") for Admin and Pharmacist.
- Cashier cannot open either page.

## Files
- `pharmacy/business_rules.py` (new): phone number rule, reminder text, WhatsApp link. No database, easy to test.
- `pharmacy/repos/business.py` (new): SQL for the closing totals and the dues list.
- `pharmacy/routes/business.py` (new): the two pages.
- `pharmacy/routes/__init__.py`: registers the new routes.
- `templates/closing.html` (new), `templates/customer_dues.html` (new).
- `templates/base.html`: two nav links.
- `tests/test_business_step5.py` (new, 27 checks).

## Tests
- Mock suite: 423 pass, 2 fail (the 2 old profile tests, unchanged).
- URL map: 66 routes. Two new (`/daily-closing`, `/customer-dues`). None removed.

## Pharmacy benefit
- End of day: the cashier and owner see the same total without adding paper bills by hand.
- Customer dues: one click sends a polite reminder; no need to write each message or copy numbers.

## Not done in Step 5 (planned for later)
- Expiry return claim (list of expiring stock to send back to the supplier): needs a new table, so it is its own step.
- Barcode field on medicines and scanning in the sale screen: needs a database column and JavaScript; next step.
- GST per item: the current tax is one rate for the whole bill; per-item GST changes the sales and invoice logic, so it needs a decision first.
- Refunds are not split by payment method (the current data does not record how a refund was paid).

## Files to put in the project
- Replace: `templates/base.html`, `pharmacy/routes/__init__.py`.
- New: `pharmacy/business_rules.py`, `pharmacy/repos/business.py`, `pharmacy/routes/business.py`, `templates/closing.html`, `templates/customer_dues.html`, `tests/test_business_step5.py`.
- Everything else stays the same.
