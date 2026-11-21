"""AI Pro helpers (Stage 6, Master Prompt v4). Pure logic, no Flask, no database.

- RateLimiter: per-user question limit for the chat endpoint.
- TTLCache: short-lived answer cache (same question, same user).
- build_summary_prompt: the daily summary prompt. It is built ONLY from
  aggregate numbers (totals and counts). Patient names, phone numbers and
  addresses are never part of it - this function cannot even receive them.
"""
import time

RATE_LIMIT = 20          # questions per user per window
RATE_WINDOW = 60         # seconds
CACHE_TTL = 600          # 10 minutes
CACHE_MAX = 200


class RateLimiter:
    def __init__(self, limit=RATE_LIMIT, window=RATE_WINDOW):
        self.limit = limit
        self.window = window
        self._hits = {}

    def allow(self, user_id, now=None):
        now = time.monotonic() if now is None else now
        hits = [t for t in self._hits.get(user_id, []) if now - t < self.window]
        if len(hits) >= self.limit:
            self._hits[user_id] = hits
            return False
        hits.append(now)
        self._hits[user_id] = hits
        return True


class TTLCache:
    def __init__(self, ttl=CACHE_TTL, max_items=CACHE_MAX):
        self.ttl = ttl
        self.max_items = max_items
        self._store = {}

    def get(self, key, now=None):
        now = time.monotonic() if now is None else now
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if now - ts > self.ttl:
            del self._store[key]
            return None
        return value

    def put(self, key, value, now=None):
        now = time.monotonic() if now is None else now
        if len(self._store) >= self.max_items:
            oldest = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest]
        self._store[key] = (now, value)


def build_summary_prompt(agg):
    """agg = aggregate numbers only: sales_today, bills_today, low_stock,
    expiring_30d, dues_total. Returns the prompt text sent to Gemini."""
    return (
        "You are the assistant of a small pharmacy shop. Here are today's aggregate shop numbers "
        "(no customer or patient information):\n"
        f"- Sales today: Rs {agg.get('sales_today', 0)} in {agg.get('bills_today', 0)} bills\n"
        f"- Items low on stock: {agg.get('low_stock', 0)}\n"
        f"- Items expiring within 30 days: {agg.get('expiring_30d', 0)}\n"
        f"- Total customer dues (udhaar) outstanding: Rs {agg.get('dues_total', 0)}\n"
        "Write a short summary for the shop owner in at most 5 lines, simple words, "
        "Roman Urdu mixed with English terms. Mention only these numbers. "
        "Do not invent any other numbers, names or advice about medicines."
    )
