# MediGen AI Pro - Step 9b (OpenAI option for the chatbot)

## What changed
- The chatbot can now use **OpenAI (ChatGPT API)** as well as Claude. Choose one in `.env`:
  - `AI_PROVIDER=openai` (or `anthropic`, the default)
  - `OPENAI_API_KEY=` your key from the OpenAI platform
  - `OPENAI_MODEL=gpt-5-mini` (change it if you want another model)
- Same rules as before: offline first; AI only for questions the offline engine does not understand;
  only the question and a fixed pharmacy prompt are sent; no shop, customer or patient data; key never shown or logged.
- If the key is empty or `AI_PROVIDER` is not set, the chatbot stays offline.

## Files
- Replace: `config.py`, `pharmacy/ai_client.py`, `pharmacy/lib.py`, `tests/test_ai_step9.py`, `.env.example` (reference only)
- New: `tests/test_ai_openai.py` (15 checks), `CHANGELOG_STEP9B_OPENAI.md`

## Tests
- Full mock suite: 522 pass, 2 fail (the 2 old profile tests, unchanged).

## Your steps
1. Replace the files above. Do not overwrite your real `.env`.
2. In `.env`, set:
   ```
   AI_PROVIDER=openai
   OPENAI_API_KEY=your_new_key_here
   OPENAI_MODEL=gpt-5-mini
   ```
3. Restart `python app.py`, then ask an unknown question in the chatbot.

## Important
- The key you shared in the chat has been exposed. Delete it on the OpenAI platform and create a new one.
- Never paste the key into chat, screenshots or project files.
