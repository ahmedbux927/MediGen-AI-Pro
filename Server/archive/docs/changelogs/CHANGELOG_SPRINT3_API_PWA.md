# Sprint 3 - REST API (read-only), API tokens, Installable PWA

## What's new

### 1. API tokens
- New table `api_tokens` (created automatically by `ensure_schema`).
- Tokens look like `mgk_...`. The raw token is shown ONCE when created. Only a SHA-256 hash is stored.
- Roles allowed for tokens: **Admin** or **Pharmacist** only.
- Create a token:

  ```
  python scripts/create_api_token.py "Label" Admin
  python scripts/create_api_token.py "Label" Pharmacist
  ```

### 2. Read-only REST API (`/api/v1/`)
Send the token as a header: `Authorization: Bearer mgk_...`

| Endpoint | Who | What |
|---|---|---|
| `GET /api/v1/health` | no token | Server status check |
| `GET /api/v1/medicines?q=&page=&per=` | Admin, Pharmacist | Medicine list (`per` max 100). `cost_price` is returned to **Admin only** |
| `GET /api/v1/stock/low` | Admin, Pharmacist | Low-stock medicines |
| `GET /api/v1/batches/expiring?days=` | Admin, Pharmacist | Batches expiring within `days` (1-365) |
| `GET /api/v1/sales/summary?from=&to=` | Admin | Sales totals for the period |

- Success responses: `{"data": [...], "meta": {"page", "per", "total"}}`.
- There are **no write routes**. The API cannot create, change or delete data.
- Revoked tokens (`revoked = 1`) are refused. `last_used` is updated on each call.

### 3. Installable app (PWA)
- `/manifest.webmanifest` - app name, icons, standalone display, theme `#0f9aa0`.
- `/sw.js` - service worker. It caches **only** GET requests for `/static/` files (cache `medigen-static-v1`). Pages and API responses are never cached.
- Icons: `static/icons/icon-192.png`, `icon-512.png`.
- `base.html` links the manifest and registers the service worker.

**Important:** browsers install the app and register the service worker only on
- `https://...` addresses, or
- `http://localhost` / `127.0.0.1`.

On a plain LAN address such as `http://192.168.x.x:5000`, the app works normally but cannot be installed and the service worker does not register. Use HTTPS (reverse proxy or hosting) for phone installs.

## Files
- New: `pharmacy/api_auth.py`, `pharmacy/routes/api.py`, `pharmacy/routes/pwa.py`, `scripts/create_api_token.py`, `static/js/sw.js`, `static/manifest.webmanifest`, `static/icons/icon-192.png`, `static/icons/icon-512.png`, `tests/test_sprint3_api.py`, this changelog.
- Changed: `pharmacy/core.py` (api_tokens table), `pharmacy/routes/__init__.py` (registers api and pwa), `templates/base.html` (manifest, theme colour, service worker).

## Tests
- `python tests/test_sprint3_api.py` - 26 checks, all pass.
- `python tests/run_all.py` - 546 passed, 0 failed.

## Install / update
1. Stop the server.
2. Replace the whole `MediGen` folder with the new one (keep your `.env` and `backups/`).
3. Run `python app.py` and press Ctrl+F5 in the browser.
4. Optional: `python scripts/create_api_token.py "My app" Admin` to create a token.
