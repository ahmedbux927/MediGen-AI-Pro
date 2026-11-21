# QA MATRIX — route × role smoke test

Run live on 2026-11-21 against the v4 tree with a real MySQL server and four
identities (anonymous, Cashier, Pharmacist, Admin). Status codes are the
actual responses. Denied pages return **302** in this app (redirect with a
"not allowed" message) — that is the app's long-standing denial style, the
same one the role_required decorator has always used.

| Route | Anon | Cashier | Pharmacist | Admin |
|---|---|---|---|---|
| /dashboard | 302 | 200 | 200 | 200 |
| /sales/new (POS) | 302 | 200 | 200 | 200 |
| /sales | 302 | 200 | 200 | 200 |
| /sales/held | 302 | 200 | 200 | 200 |
| /medicines | 302 | 200 | 200 | 200 |
| /products/medicines (section) | 302 | 200 | 200 | 200 |
| /products/import-preview | 302 | 302 | 200 | 200 |
| /customers | 302 | 200 | 200 | 200 |
| /customer-dues | 302 | 302 | 200 | 200 |
| /cash | 302 | 200 | 200 | 200 |
| /cold-chain | 302 | 200 | 200 | 200 |
| /expiry-clearance | 302 | 200 | 200 | 200 |
| /refills | 302 | 200 | 200 | 200 |
| /chatbot | 302 | 200 | 200 | 200 |
| /batches | 302 | 302 | 200 | 200 |
| /alerts | 302 | 302 | 200 | 200 |
| /data-quality | 302 | 302 | 200 | 200 |
| /stock-count | 302 | 302 | 200 | 200 |
| /controlled-register | 302 | 302 | 200 | 200 |
| /prescriptions | 302 | 302 | 200 | 200 |
| /interactions | 302 | 302 | 200 | 200 |
| /inspection-report | 302 | 302 | 200 | 200 |
| /purchase/suggestions | 302 | 302 | 200 | 200 |
| /purchase/drafts | 302 | 302 | 200 | 200 |
| /purchase/forecast | 302 | 302 | 200 | 200 |
| /supplier-returns | 302 | 302 | 200 | 200 |
| /suppliers | 302 | 302 | 200 | 200 |
| /expenses | 302 | 302 | 200 | 200 |
| /daily-closing | 302 | 302 | 200 | 200 |
| /margins | 302 | 302 | 200 | 200 |
| /purchase (list) | 302 | 302 | 302 | 200 |
| /purchase/new | 302 | 302 | 302 | 200 |
| /supplier-summary | 302 | 302 | 302 | 200 |
| /reports | 302 | 302 | 302 | 200 |
| /digest | 302 | 302 | 302 | 200 |
| /activity-log | 302 | 302 | 302 | 200 |
| /users | 302 | 302 | 302 | 200 |
| /settings | 302 | 302 | 302 | 200 |

Notes on the design (observed, unchanged — business rules are the owner's):
- Purchasing list, receiving (/purchase/new) and supplier summary are
  Admin-only; Pharmacist gets suggestions, drafts, forecast and returns.
- Reports, Daily Digest, Activity Log, Users and Settings are Admin-only.
- Cashier keeps the full counter set (POS, sales, held bills, medicines,
  customers, cash drawer, cold chain, expiry clearance, refills, chatbot).

## Security checks run the same day (live)

- **CSRF:** a POST without a token (as a logged-in Admin, to
  /settings/reset) was rejected — redirected to /login and the setting was
  NOT changed (verified in the database). Tokens are auto-injected into
  forms and also accepted via the X-CSRFToken header (chat API).
- **Cookies:** the session cookie is HttpOnly with SameSite set.
- **SQL:** parameterized queries throughout (audited in Stage 2/v100);
  f-string SQL only interpolates whitelisted table/column names.
- **Uploads:** import files are capped (CSV/photo via MAX_BYTES, PDF 10 MB)
  and parsed, never executed; the photo OCR path deletes the upload after
  reading.
- **Debug:** the shipped config keeps debug off; the server runs on waitress.

## Migrations double-run (fresh database)

- Fresh MySQL database + schema.sql + sample_data.sql (the documented
  install path; both files pin the shop database name by design).
- First app startup applied migrations 2–14 (schema_version), creating
  everything schema.sql does not carry (held bills, sale guard, agent
  actions, import tables, units_per_pack, ...).
- Second startup applied **nothing** and logged no errors; server healthy.
  Each migration is also written to run twice without error.

## Performance (fake data, sandbox VM — slower than a shop PC)

1005 medicines and 10,005 batches were seeded into a scratch database.
Steady-state response times (local server, warm):

| Page | Time | Size |
|---|---|---|
| POS /sales/new (full catalog) | ~300–350 ms | 765 KB |
| Medicines /medicines | ~520–550 ms | 2.6 MB |
| Dashboard /dashboard | ~280 ms | 52 KB |

The POS catalog SQL itself takes ~0.2 s (batches.medicine_id is indexed;
the catalog is one query, no N+1). First hit after a cold start is slower
(template compile + buffer pool warm-up); the counter flow itself (search
and add-to-cart) is client-side and instant once the page is open. The
Medicines page is the heaviest page in the app (every row with its edit
dialogs); it still loads in about half a second locally at 1000 items.
