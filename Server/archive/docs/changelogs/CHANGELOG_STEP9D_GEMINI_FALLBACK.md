# MediGen AI Pro - Step 9d (Gemini fallback models)

## What changed
- If the main Gemini model is busy (HTTP 503) or over its limit (HTTP 429), the app now tries the next model automatically.
- Default order: `GEMINI_MODEL`, then `gemini-2.5-flash-lite`, then `gemini-2.5-flash`.
- Errors such as a wrong key (400) or no permission (403) are not retried, because another model will not fix them.
- Optional `.env` line (default already set):
  `GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite,gemini-2.5-flash`

## Files
- Replace: `config.py`, `pharmacy/ai_client.py`, `tests/test_ai_gemini.py`, `.env.example` (reference only)

## Tests
- Full mock suite: 538 pass, 0 fail.
- New checks: busy model falls back to the next model; bad key is not retried.

## Your steps
1. Replace the files above. Do not overwrite your real `.env`.
2. Restart `python app.py`, then run `python scripts/test_gemini.py`.
