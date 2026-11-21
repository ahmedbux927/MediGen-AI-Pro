# MediGen AI Pro - Step 11N: Customers Table Fix

## Problem
On the Customers page the table was wider than its card, so the Action column (delete button) was cut off at the right edge.

## Fix (CSS only, in `static/css/pages.css` v24)
- `.data-card` scrolls horizontally when needed instead of clipping.
- `.data-table` has a minimum width of 860px, so every column stays readable.
- The Action column has enough right padding and does not wrap.
- Action button design is unchanged. No template changes.

## Audit and backup
Kept as they are (already styled in 11M). Both pages look professional.

## Verified
- At 1440px the table fits inside the card, and the last column ends inside the card edge.
- At 1024px the card scrolls, so the Action column is reachable and not clipped.
- Tests: 584 passed, 0 failed.

## Install
1. Replace the whole project folder.
2. `python app.py`, then Ctrl+F5.
3. `python tests/run_all.py` (expect 584 passed).
