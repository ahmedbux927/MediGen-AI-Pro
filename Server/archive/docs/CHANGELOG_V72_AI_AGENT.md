# MediGen v72 - AI agent: chat write commands with Confirm (Phase 3 core)

## What changed
- Chat can now propose two data changes. Nothing is saved until the user presses **Confirm**:
  - `shelf Panadol to A-3`  /  `Panadol ka shelf A-3`  → set shelf location
  - `add customer Ali Khan 0300-1234567`  /  `naya customer Sara` → add customer
- The chat shows the proposal and a Confirm / Cancel pair. The confirmation token is valid 5 minutes and works once.
- Only Admin and Pharmacist can propose or confirm. Cashier gets a polite refusal.
- Read questions (low stock, expiry, etc.) still go to the existing offline chat engine, unchanged.

## Backend
- `pharmacy/services/agent_router.py` (new): parses chat text into write proposals. Pure function, no database.
- `pharmacy/services/agent_tools.py`: `ensure_agent_table()` creates `agent_actions` at runtime (same definition as migration 007).
- `pharmacy/routes/chatbot.py`: `/chatbot/api` sends write commands to the agent first; history is saved without the token.
- `pharmacy/routes/agent.py` (new): `POST /agent/confirm` runs the confirmed change, rolls back on any error, returns a short result text.
- `pharmacy/routes/__init__.py`: registers the agent routes.

## Front-end
- `templates/chatbot.html`: `addConfirm()` / `confirmToken()` buttons. No static file changes, so no cache bump.

## Tests
- `tests/test_agent_router.py` (new, 19 checks).
- `tests/run_all.py`: 1370 passed, 0 failed.
- Freeze manifest regenerated.
- Not verified: a real MySQL run (`run_all.py --live`) and the Confirm button in a real browser.

## Check on the shop PC
1. Copy v72 over the project (keep `.env` and `logs`), restart, Ctrl+F5.
2. Chat: `shelf <exact medicine name> to A-3` → Confirm → the medicine list shows `· A-3`.
3. Chat: `add customer Test 0300-1234567` → Confirm → the customer appears in Customers.
4. Log in as Cashier and try the same: it should be refused.
