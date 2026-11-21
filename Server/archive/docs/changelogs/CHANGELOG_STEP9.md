# MediGen AI Pro - Step 9 (Chatbot with optional Claude API, offline first)

## What changed
- The chatbot still works fully offline. It answers stock, sales, expiry, dues and customer questions from the database as before.
- Only when the offline engine says "I did not understand", AND a key is set in `.env`, the question is sent to Claude.
  - Reply is shown with a note: *AI answer. Please verify with a licensed pharmacist before any clinical decision.*
  - If Claude is down, the key is wrong, or the internet is off, the normal offline message is shown. Nothing breaks.
- **Privacy:** only the typed question (max 300 characters) and a fixed pharmacy prompt are sent.
  No customer, patient, sales, stock or user data is sent. The key is never shown in the browser, in logs or in chat history.
- Settings added in `.env` (all optional):
  - `CLAUDE_API_KEY` (empty = offline only)
  - `CLAUDE_MODEL` (default `claude-haiku-5-5`)
  - `CLAUDE_TIMEOUT` (default 15 seconds)
  - `AI_ENABLED` (default 1; set 0 to switch AI off without removing the key)

## Files
- New: `pharmacy/ai_client.py` (Claude call, uses only Python standard library, no new package)
- Changed: `pharmacy/lib.py`, `pharmacy/core.py`, `chatbot_engine.py`, `config.py`
- New test: `tests/test_ai_step9.py` (23 checks, mock network, no real API call)
- Reference only: `.env.example` (do not overwrite your real `.env`)

## Tests
- Full mock suite: 496 pass, 2 fail (the 2 old profile tests, unchanged).
- Step 9 checks cover: AI off without key, no network when off, correct endpoint and headers,
  only the question is sent, no shop data in request, key not in body or chat response,
  timeouts and HTTP 401 handled, Claude used only for unknown questions, offline message when Claude is down.
- Not tested against the real Anthropic service from this environment (no internet access here).

## Pharmacy benefit
- Staff can ask in plain English or Roman Urdu. Questions the shop software cannot read still get a helpful answer
  when internet is available. Shop data stays on the shop computer.

## Your steps
1. Replace the changed files listed above. Put the new files in place.
2. Open your real `.env` and add the lines from `.env.example` (only the 4 AI lines). Add your key after `CLAUDE_API_KEY=`.
   Do not paste the key into any chat, screenshot or file in the project.
3. Restart `python app.py`.
4. Type an unknown question, for example "kya aap bata sakte hain xyz". Expect the AI note.
   Leave `CLAUDE_API_KEY` empty to confirm the offline message.
