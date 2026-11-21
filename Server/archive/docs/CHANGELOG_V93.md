# MediGen AI Pro — v93.00 changes

## Frontend: "Signature" professional look (owner-approved demo, then full rollout)
- NEW static/css/v93-theme.css (loads after v92-theme.css): glassy top bar with blur,
  soft aurora page background, deeper rounded cards (20px) with layered shadows and
  hover lift, staggered page entrance (respecting prefers-reduced-motion), gradient
  KPI icon tiles and bigger Jakarta numerals on the dashboard.
- Sidebar is now PROFESSIONAL GRAPHITE (deep charcoal gradient, silver accents,
  muted steel active pill). The bright blue sidebar and the bright blue/violet
  brand gradient are gone (--mg-grad / --brand-grad retinted to deep slate);
  the dashboard's tez teal KPI colour is muted to steel. No green brand colour.
- Premium fonts BUNDLED with the program (static/fonts/: Inter + Plus Jakarta Sans,
  woff2, ~330 KB) — the same look with or without internet on the shop PC.
- POS (New Sale): larger tactile product cards with hover lift, gradient count
  badge, a sticky gradient BILL BAR (items + total always visible), hero scan box.
  Dark mode: product cards are proper dark tiles now (they stayed white before).
- Ctrl+K COMMAND PALETTE on every page: type to jump to Dashboard, New Sale,
  Sales, Medicines, Inventory, Purchasing, Finance, Cash Drawer or Admin.
  Arrow keys + Enter work; Esc closes.
- Success flash bars muted to slate-mint (professional, not bright green).

## Bug fix: list import now carries RATES (owner requirement: stock + rates + category)
- pharmacy/services/product_sections.py: the section CSV parser never read a price
  column and import_items hard-wrote price 0 — every imported medicine/syrup/cream
  landed with rate Rs 0. The parser now reads price/rate/sale_price/mrp and
  cost_price/trade_price columns, and import_items writes them.
- PDF lists had the same gap one layer earlier: pdf_to_csv_bytes converted tables
  to a fixed schema WITHOUT price. _table_records now maps Price/Rate columns and
  STD_COLS includes price + cost_price.
- Verified live: CSV import (Benadryl Rs 180, stock 25, Syrups category) and PDF
  import (Calamine Rs 220, stock 15, Creams category) land with rate + stock +
  category; an imported item was then sold on the POS and produced its invoice.
- Note: the classic Drip page's own CSV format stays as designed (names/forms only;
  its message tells the user to set price/stock). The Drip & Injection SECTION page
  import (CSV/PDF) carries rates like every other section.

## Sample import lists (top-level Import_Lists/ folder)
- MediGen_Import_Medicines / Syrups / Creams / Injections, each as .csv AND .pdf —
  realistic items with form, strength, sale rate, cost and stock. Open a section
  page, choose "Import list", pick the file. All 8 files were import-tested here.

## Full check (this build, real runs)
- Every page crawled signed-in: 56 routes, no 500s (the one "error" text found was
  the chatbot page's own JavaScript fallback string, not an error).
- Real browser + database flows: medicine add -> edit (price) -> delete; purchase
  saved (Panadol stock 500 -> 550); Card sale of an imported syrup -> thermal
  invoice, stock 25 -> 24; Settings save; Profile update; add Cashier user.
- Test suites: mock 2391 passed / 0 failed; full incl. live MySQL 2446 / 0.
  (Four older tests pinned version "92.00" and one pinned the old import
  behaviour "price stays 0" — updated to the v93 contracts.)
- Still unverified, as before: Windows .bat scripts on a real Windows PC, and a
  real Gemini answer with the owner's own API key (Settings -> AI Assistant ->
  Test connection gives the verdict on the shop PC).
