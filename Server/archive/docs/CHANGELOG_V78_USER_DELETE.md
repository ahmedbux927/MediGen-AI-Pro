# MediGen v78 - Clear user delete rules (includes v72-v77)

## Why
- A user who has sales is never deleted, only turned OFF, so the history keeps working. The old message was too short, and the confirm box still said "Delete this user?", so it looked like a bug (e.g. "Hassain cannot be deleted").
- The old check only looked at sales and chat messages. Other work records (stock changes, drip records, assistant actions, etc.) were not checked, so a user with only those could be deleted and their history would lose the name.

## What changed
- Delete now checks **every table that has a user_id** (except audit lines, which are written at each login and keep the username as text anyway).
- Login rows (remember tokens, reset codes, API tokens) are always removed.
- If any work record exists → account is turned **OFF**. Message says what was found, e.g. "has work history (12 sales, 3 stock changes)… Nothing was lost. Use the power button to turn it back on."
- If no work record exists → user is **deleted**.
- Confirm box and tooltip now say that the account may be turned OFF instead.

## Files
- `pharmacy/services/user_history.py` (new): the rules and plain-word summary.
- `pharmacy/routes/users.py`: `delete_user` uses the rules.
- `templates/users.html`: confirm text and tooltip.
- `tests/test_user_delete_rules.py` (new, 13 checks).
- `tests/test_coverage_admin.py`: mock updated for the new history check.

## Tests
- `tests/run_all.py`: 1493 passed, 0 failed. Freeze manifest regenerated.

## Not changed (needs a decision from you)
- A user with history can still not be deleted completely. Doing that would remove or re-assign their sales and stock records, which affects money and audit. Turning OFF is the safe rule.
- If you want a real delete, tell me who should own the old records (for example, the admin) and I will add a separate, double-confirmed action.

## Open: "users cannot be added past 4-5"
- No count limit exists in the code. The cause is probably an error message on the shop PC. Please send the last lines of `logs\medigen.log` after trying to add a user, so the real error can be fixed.

## Check on the shop PC
1. Copy v78 over the project (keep `.env` and `logs`), restart, Ctrl+F5.
2. Users → delete a test user who never made a sale: they should be deleted.
3. Users → delete a user with sales: the message should say the account was turned OFF and nothing was lost.
