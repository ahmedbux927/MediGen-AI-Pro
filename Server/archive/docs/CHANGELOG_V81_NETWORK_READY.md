# MediGen v81 - Works on shop WiFi and from outside (VPN), data stays safe

## What changed
- `.env.example` is now ready for both places:
  - `APP_HOST=0.0.0.0`: the app listens on the shop WiFi and the VPN.
  - `ALLOWED_NETWORKS=192.168.0.0/16,100.64.0.0/10`: only shop WiFi and Tailscale addresses can open it. Everyone else gets a 403.
- START_MEDIGEN.bat (v80) still starts the app with one double-click.

## Your data
- Your real shop data stays in your own MySQL database. This zip does not contain it and does not replace it.
- On the first start, the app checks the database and creates any missing tables and columns by itself (`ensure_schema`). New tables (drip records, assistant actions, login attempts, prescription photos folder) are created when first used. Existing sales, medicines, customers and users are not changed.
- Do not run `database/schema.sql` on the live database. It is for an empty database only.

## Steps for the shop PC
1. Make a backup first: MySQL Workbench → Server → Data Export → select `pharmacy_management_system` → export to a file (for example `C:\MediGen_backup.sql`). Keep it safe.
2. Copy the new project files over the old folder. Keep your `.env` file (or update it with the two lines above) and keep the `logs` folder.
3. Double-click START_MEDIGEN.bat.
4. Open `http://127.0.0.1:5000` on the PC. Then, from another phone on the shop WiFi, open the address the window shows.
5. For the owner outside the shop: set up Tailscale (see CHANGELOG_V79_REMOTE_ACCESS.md), then open `http://<tailscale-address>:5000` on the owner's phone.

## Firewall
- Allow port 5000 on the Private network only. Do not allow it on Public networks, and do not forward it on the router.

## Tests
- `tests/run_all.py`: 1508 passed, 0 failed. Code change is only the example settings and one outdated test check (`test_android_lan.py`) updated to match them.
