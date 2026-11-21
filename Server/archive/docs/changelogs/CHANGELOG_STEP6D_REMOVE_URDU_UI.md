# MediGen AI Pro - Step 6D: Roman Urdu UI removed

## Why
The client asked to remove the Roman Urdu page language. The whole UI is English again. The greeting stays "Good morning / afternoon / evening".

## Removed
- The "Roman Urdu" / "English" button in the top bar, and its `/language` route (`pharmacy/routes/language.py`).
- `pharmacy/i18n.py` (labels table and the flash message list).
- The language helpers in `pharmacy/lib.py` (`t()`, `tf()` and `inject_language`).
- Page labels added in Step 6 part 2 on Dashboard, Medicines, Customers, Sales and New Sale. These pages are back to the English text.
- Tests: `tests/test_i18n_step6.py`, `tests/test_step6b_labels.py`.

## Kept
- Chatbot still answers in English or Roman Urdu depending on the question (AI Assistant page).
- The Language field on the user profile (stored as text, not used for page labels).

## Test
- Full suite: 481 passed, 0 failed.

## Install
1. Replace the project folder.
2. `python app.py`, then Ctrl+F5.
