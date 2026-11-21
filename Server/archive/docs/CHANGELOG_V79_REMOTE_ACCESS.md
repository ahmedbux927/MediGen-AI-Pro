# MediGen v79 - Owner access from anywhere, safely (Tailscale VPN + network allow-list)

## What changed
- New setting **ALLOWED_NETWORKS** in `.env`. Only addresses inside the listed networks may open the app. Anything else gets a plain "403" message and is logged as a warning.
  - `192.168.0.0/16` = shop WiFi / LAN
  - `100.64.0.0/10` = Tailscale VPN (owner's phone or laptop, from anywhere)
  - This PC (127.0.0.1) is always allowed.
  - Empty = no limit (the old behaviour, so nothing breaks until you set it).
- The check runs first, before login, so a stranger cannot even reach the login page.
- Bad entries in the list are ignored (and reported in the code), the good ones still work.
- Existing protections stay: login lockout after wrong passwords, role limits (Admin / Pharmacist / Cashier).

## Roles (as you described)
- **Cashier**: counter only (sales, POS, customers). Cannot change prices, users or settings.
- **Pharmacist (owner, Admin role)**: full access. Can open the app from anywhere over the VPN.

## Files
- `pharmacy/services/net_access.py` (new): parse the list, decide allowed or not.
- `pharmacy/core.py`: `_network_gate` before-request check.
- `config.py`: `ALLOWED_NETWORKS`.
- `.env.example`: example line.
- `tests/test_network_access.py` (new, 15 checks).

## Tests
- `tests/run_all.py`: 1508 passed, 0 failed. Freeze manifest regenerated.
- Not tested with a real Tailscale connection. Test on the shop PC first.

## Setup on the shop PC (Windows), step by step
1. Install **Tailscale** on the shop PC and on the owner's phone/laptop. Sign in with the same account on both. (tailscale.com → Download)
2. On the shop PC open Tailscale; note its address (starts with 100.). Check it with `tailscale ip -4` in Command Prompt.
3. Edit `.env` in the project folder:
   ```
   APP_HOST=0.0.0.0
   ALLOWED_NETWORKS=192.168.0.0/16,100.64.0.0/10
   ```
4. Windows Firewall: allow port **5000** for the **Private** network (and for Tailscale, if asked). Do not allow it for Public networks.
5. Restart the app (close the old window first).
6. On the owner's phone (Tailscale ON, same account), open `http://100.x.y.z:5000` (the address from step 2).
7. Check the cashier counter still works on the shop WiFi (192.168.x.x).

## Security reminders
- Tailscale encrypts the connection end to end, so plain http on the VPN address is acceptable. Do not open port 5000 to the public internet.
- Use a strong Admin password. Do not share `.env`.
- Rotate the MySQL password and SECRET_KEY if they were ever pasted in chat or shared.
- If someone on the list leaves the shop, remove their Tailscale device and change their app password.
