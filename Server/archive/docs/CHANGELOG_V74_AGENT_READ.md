# MediGen v74 - Agent read-only queries: shelf location and phone lookup (includes v72/v73)

## What changed
- Chat understands two read-only questions. These never change data and need no Confirm:
  - **Shelf / where is a medicine:** `shelf Panadol`, `Panadol ka shelf`, `where is Panadol`, `kahan hai Panadol`.
    Answer: name, shelf (or "shelf not set"), stock and price. Up to 10 results.
  - **Customer by phone:** `0300-1234567` or `customer 03001234567` (4+ digits).
    Answer: name, number and udhaar balance.
- Everything else (stock, low stock, expiry, sales) still goes to the existing chat engine, unchanged.
- Any logged-in user can ask these (Cashier included), since they only read.
- Write commands are checked first, so `shelf Panadol to A-3` is still a proposal with Confirm.

## Backend
- `pharmacy/services/agent_router.py`: `parse_read()`, `shelf_answer()`, `customer_answer()` (pure functions).
- `pharmacy/routes/chatbot.py`: `_agent_read()` uses `agent_tools.find_medicine` and `find_customer` (SELECT only).

## Tests
- `tests/test_agent_read.py` (new, 21 checks).
- `tests/run_all.py`: 1407 passed, 0 failed.
- Freeze manifest regenerated.
- Not verified: `run_all.py --live` against MySQL and the chat bubble in a real browser.

## Check on the shop PC
1. Copy v74 over the project (keep `.env` and `logs`), restart, Ctrl+F5.
2. Chat: `shelf Panadol` → shelf and stock lines.
3. Chat: `0300-1234567` (a saved customer's number) → customer with balance if any.
4. Chat: `Panadol stock` → still answered by the old engine.
