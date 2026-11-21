# Step 28 (v49.8): Phase 4 backend, compliance (register, prescription rule, cold chain)

Backend only. No template or static file changed (freeze test passes).

## What changed
1. Migration `005_controlled_register.sql`: table `controlled_register` (one row per batch part sold of a scheduled medicine).
2. Migration `006_temperature_logs.sql`: table `temperature_logs` (location, temperature, in_range flag, user, note).
3. `pharmacy/services/controlled_register.py`:
   - `scheduled_items`: medicines whose `schedule` is set by the pharmacist.
   - `prescription_missing`: scheduled medicine on a bill with no prescription is refused.
   - `entries_for_sale` / `write_entries`: one register row per batch part.
   - `ensure_register_triggers`: append-only (UPDATE and DELETE blocked). If the DB user lacks TRIGGER permission, the app logs a warning and still starts.
4. `pharmacy/services/temperature.py`: reading parser (accepts `5.2` or `5,2`, rejects non-numbers and impossible values), range check 2.0 to 8.0 C by default, reading saved even when out of range (`in_range = 0`).
5. `pharmacy/services/sales.py`: `check_scheduled` (runs after stock is reserved, before the bill is saved); `save_sale(..., scheduled=None)` writes register rows only when scheduled items exist.
6. `pharmacy/routes/sales.py`: calls `check_scheduled` and passes `scheduled` to `save_sale`. No other route change.
7. `pharmacy/core.py`: imports and calls `ensure_register_triggers` after the migrations.
8. `tests/test_phase4_backend.py`: 29 mock checks.

## Behaviour change to know about
- A medicine with NO schedule value behaves exactly as before.
- A medicine WITH a schedule value now needs a prescription on the bill (`prescription_id`). The sale is refused with: "Prescription needed for: <name>. Attach the prescription to this bill."
- The pharmacist sets `medicines.schedule`. Until it is set, nothing changes.

## Not confirmed (needs the pharmacist / drug authority)
- Which medicines are controlled, and the schedule names.
- The official register layout and retention period.
- Whether buyer identity (CNIC, address) must be recorded. The table currently stores customer_id only; it does not store CNIC.
- Cold-chain range per product. Default 2 to 8 C applies to all locations.

## Tests
- `python tests/run_all.py`: 1276 passed, 0 failed (mock DB).
- Not yet run against real MySQL. Live checks (register triggers, FOR UPDATE on schedule lookup, migration 005/006 creation) need `python tests/run_all.py --live` on the shop PC with a server.

## Not in this step
- Screens for the register and temperature log (frontend parked).
- Daily report lines for temperature out-of-range (planned, not built).
