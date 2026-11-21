# MediGen AI Pro — v92.00 (2026-11-20)

Fix release for three complaints from the owner's own screenshots:
Gemini key saved but assistant still not like Gemini, green frontend not
liked, and writing invisible in dark mode.

## What changed

### Theme — "Midnight Sapphire" (green is gone)
- New `static/css/v92-theme.css` replaces v91-theme.css: deep-navy sidebar
  (#0b1737), sapphire-to-violet gradient buttons and accents, navy welcome
  banner. `--brand-grad` recoloured so every component that reads it
  (hero icons, active tabs, primary buttons) follows.
- Chatbot page gradients retinted sapphire/violet; sale table header navy.
- Top-bar squeeze fixed: page heading and welcome line are nowrap with
  ellipsis, the user badge never wraps, the date chip hides below 1280px —
  so a long name (e.g. "Syrups & Suspensions" / "Ahmed Bux Banbhan") can no
  longer crush the heading the way the owner's screenshot showed.

### Dark mode — writing fixed in every section (21 pages x 2 modes audited)
- Dashboard owner KPI row + Section records table: the template's `.dv`
  variables were only ever set to light values; dark mode now redefines
  `--ink #e8eef7`, `--d-card #0d1830`.
- Batch stat values (`.bt-card .val`), report stat values (`.rstat .val`),
  reports tab bar + filter bar, prescription cards (`.rxp-*`), and the
  profile page (`.ai-insights-card`, `.ai-stat-item`, `.form-section`,
  `.profile-tabs`) all got dark background+text pairs.
- Settings hero, avatar tile and active tab recoloured navy/sapphire;
  Test connection button is a proper ghost button in both modes.
- Grid/utility shim: several pages (Expenses, Cash Drawer, Customers,
  Medicines, Profile) were written with Bootstrap-style grid classes that
  no stylesheet defined, so forms stair-stepped and stat cards stacked
  full-width. The shim restores the intended layout (verified: Expenses
  form is one clean row, Medicines shows 4 cards in a row).

### AI key diagnostics (the real defect was silence, not the wiring)
- `ai_client.test_provider()` + `friendly_reason()`: one tiny live call
  with the saved key, and a plain-English reason for every failure
  (HTTP 400 invalid key, 401/403 key refused, 404 model missing,
  429 rate limit, 500 provider problem, no network).
- New `POST /settings/ai/test` (Admin only) + a "Test connection" button
  under each key in Settings → AI Assistant. It shows the provider's
  real verdict on the spot.
- The chat no longer fails silently: when the online AI is set up but
  does not answer, the reply now says why, and points to Test connection.
- Verified live: with a (fake) key saved, the chat header showed ONLINE,
  a general question reached Gemini's endpoint, and the failure reason was
  displayed in the chat and in the Test button.

## Tests (run in the build VM, real MySQL 8.0.46)
- `tests/test_v92_pro.py`: 49 passed, 0 failed.
- Full mock suite: 2373 passed, 0 failed.
- Full suite incl. live MySQL: 2428 passed, 0 failed.

## Still unverified (honest)
- Windows .bat scripts on a real Windows PC.
- A real Gemini answer with the owner's own key — the build sandbox
  cannot complete a live call to Google (its urllib POST stalls; curl
  reaches Google fine). On the shop PC, Test connection gives the
  verdict in seconds: if it says "key refused", the key itself is wrong
  — copy it again from aistudio.google.com.

## Install
Replace the WHOLE old Server folder (not file-by-file). First preserve
`.env`, the `backups/` folder and `static/profiles/` images, restore them
after, then run START_DESKTOP.bat.
