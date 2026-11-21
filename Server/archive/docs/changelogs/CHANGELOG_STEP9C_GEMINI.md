# MediGen AI Pro - Step 9c (Gemini option for the chatbot)

## What changed
- The chatbot can use **Google Gemini** (model `gemini-2.5-flash` by default). Set in `.env`:
  - `AI_PROVIDER=gemini`
  - `GEMINI_API_KEY=` your new key from Google AI Studio
  - `GEMINI_MODEL=gemini-2.5-flash`
- Same rules as before: offline first; AI only for questions the offline engine cannot read; only the question and a fixed pharmacy prompt are sent; no shop, customer or patient data; key never shown or logged.
- New test script: `scripts/test_gemini.py` checks your key directly. Run `python scripts/test_gemini.py` from the project folder.

## Files
- Replace: `config.py`, `pharmacy/ai_client.py`, `.env.example` (reference only)
- New: `scripts/test_gemini.py`, `tests/test_ai_gemini.py` (12 checks), `CHANGELOG_STEP9C_GEMINI.md`

## Tests
- Full mock suite: 536 pass, 0 fail.
- Not yet checked against the live Gemini service: run `scripts/test_gemini.py` with your real key to confirm.

## Your steps
1. Create a new key in Google AI Studio. Do not paste it into chat or screenshots.
2. In `.env` set:
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_new_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
3. Run `python scripts/test_gemini.py`. You should see the MediGen intro. If not, the message shows the reason.
4. Restart `python app.py`.

## Note
- The terminal earlier showed "Claude API returned HTTP 401" while the Claude key was empty. That came from an old running server. Restarting fixes it.
