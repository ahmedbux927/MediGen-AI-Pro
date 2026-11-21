# Step 32 (v54): error codes, POS checkout API, AI agent tool layer (backend only)

No template or static file changed (freeze test passes).

## 1. Error codes
- `pharmacy/lib.py`: `ERROR_CODES` (medicine_add E-102, medicine_edit E-103, sale_save E-201, user_delete E-301,
  password_reset E-401, reset_code E-402, api_checkout E-501, agent E-601).
- `flash_unexpected(message, code=None)`: the user sees "... Error E-102. Please try again. ... check the log."
  The log line carries the same code.
- Applied to: add medicine (E-102), POS checkout API (E-501).
- `audit_as(...)`: audit rows for API calls (no browser session).

## 2. Medicine columns: NOT added (already exist)
- `barcode` exists, UNIQUE index `uq_medicines_barcode` (from ensure_schema).
- `strength` exists.
- `dosage_form` exists and is the same as the requested `form`.
- `rack_location` exists and is the same as the requested `shelf_location`.
Adding duplicate columns would split the data. Renaming needs a decision (templates use the current names).

## 3. POS checkout API
- `POST /api/pos/checkout` (Bearer token, Admin or Pharmacist token linked to a user).
- Body: `items` (barcode or medicine_id, quantity), `payment_method`, `customer_id`, `discount`, `discount_type`,
  `paid`, `prescription_id`.
- Returns 201 `{sale_id, total, paid, balance}`; 400 for a problem the cashier fixes; 409 for the same bill sent
  again within 10 seconds; 403 when the token has no user; 500 with Error E-501.
- Same rules as the counter (`services/sales.py`): stock lock, FIFO batches, prescription rule, discount caps,
  udhaar needs a customer, double-submit guard.
- `api_tokens.user_id` (new, legacy ADD COLUMN in ensure_schema). `scripts/create_api_token.py "Label" Admin|Pharmacist [username]`.

## 4. AI agent tool layer (`pharmacy/services/agent_tools.py`, migration 007)
- READ (SELECT only): find_medicine, low_stock, expiring, today_summary, find_customer.
- WRITE (whitelist: set_shelf_location, add_customer), two steps:
  - propose(): stores the change, returns a token `agt_...` valid 5 minutes. Only its SHA-256 is stored.
    A new proposal cancels the user's older pending one.
  - confirm(): same user only, single use, not expired. Done mark and change in one transaction.
- No route yet: the chatbot/agent will call these functions in a later step.

## Tests
- test_pos_checkout.py: 20 checks. test_agent_tools.py: 27 checks. test_error_codes.py: 6 checks.
- Updated test_coverage_medicines.py expectation for the new add-medicine message (E-102).
- Full suite: 1341 pass, 0 fail (mock DB). Live MySQL NOT run.

## Not in this step
- Agent route/UI, voice, camera barcode scan, mobile app, prescription OCR, online store (see plan).
