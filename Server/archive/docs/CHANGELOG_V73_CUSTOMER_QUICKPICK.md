# MediGen v73 - Customer quick-pick by phone at billing (includes v72 AI agent)

## What changed
- **Billing page (POS):** a phone box above the customer dropdown.
  - Type 4+ digits (any format: `0300-1234567`, `+92 300 1234567`, `03001234567`). Matching customers appear within about 200 ms.
  - Click a result, or press **Enter** to pick the first one. The customer dropdown is set automatically.
  - Customers who owe money show "owes Rs. …" in red.
  - No match → "Add new customer with <number>". This opens the Add Customer window with the number already filled in.
- The phone search reuses the existing `pharmacy/services/phone_search.py` (same rules the agent uses).
- Includes the v72 AI agent (chat `shelf …` and `add customer …` with Confirm). See CHANGELOG_V72_AI_AGENT.md.

## Backend
- `pharmacy/routes/customer_search.py` (new): `GET /customers/search?phone=` → JSON list (max 8). Needs a logged-in session.
- `pharmacy/routes/__init__.py`: registers the route.

## Front-end
- `templates/new_sale.html`: phone box, results list, small styles, quick-add prefill (`#quickContact`).

## Tests
- `tests/test_customer_quickpick.py` (new, 15 checks, phone formats + wiring).
- `tests/run_all.py`: 1386 passed, 0 failed.
- Freeze manifest regenerated.
- Not verified: the live dropdown sync in a real browser, and `run_all.py --live` against MySQL.

## Check on the shop PC
1. Copy v73 over the project (keep `.env` and `logs`), restart, Ctrl+F5.
2. Sales → New Sale. Type the last digits of a saved customer's phone. Click the result; the dropdown should show that customer.
3. Type a number that does not exist → click "Add new customer with …" → the number is already in the form.
4. Chat: `shelf <medicine> to A-3` → Confirm (Admin/Pharmacist only).
