# MediGen v67 - Visible validation in every popup form

## Problem
- In a popup (Add Medicine, Add Customer, Edit, etc.), Save with an empty required field did nothing visible.
  The browser's own bubble could appear off-screen inside the popup. The shop saw "Save is blocked".

## Fix
- static/js/app.js: for any form inside a popup (.modal), the missing field is shown as a red message at the top of the popup,
  e.g. "Please fill: Full Name." The field gets focus and the form is not sent.
- The message hides again when the person types in the popup.
- Pages without popups keep the browser's own message.
- Add Medicine (v66) keeps its own check and note.

## Tested
- Playwright with local Bootstrap: Add Customer, Save with empty name -> "Please fill: Full Name.", no POST; after typing the message hides.
- tests/run_all.py: 1341 passed, 0 failed. Freeze manifest refreshed.

## Shop PC check
- Try Save with empty fields on Add Medicine, Add Customer, Add Supplier and Add User. Each should show a red message in the popup.
