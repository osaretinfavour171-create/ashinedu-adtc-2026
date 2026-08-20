"""LRU response cache for PidginPharma.

Caches normalized query -> answer mappings so repeated queries return
instantly without hitting the LLM. Key design decisions:

  - Cache key is the NORMALIZED English query (not raw Pidgin input),
    so "my pikin get hot body" and "my child has fever" both hit the
    same cache entry if they normalize to the same query.
  - TTL-based expiry: clinical data doesn't change during a session,
    but we expire after 4 hours to pick up any data reloads.
  - Thread-safe via threading.Lock (relevant if we ever go async).
  - Max 200 entries (~200 KB RAM) — more than enough for a PHC session.
"""

import hashlib
import threading
import time
from collections import OrderedDict

DEFAULT_MAX_SIZE = 200
DEFAULT_TTL_SECONDS = 4 * 60 * 60  # 4 hours


class ResponseCache:
    """Simple LRU cache with TTL expiry for clinical query answers."""

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE,
                 ttl_seconds: float = DEFAULT_TTL_SECONDS):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(normalized_query: str, lang: str) -> str:
        """Deterministic cache key from normalized query + output language."""
        raw = f"{normalized_query.strip().lower()}|{lang}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, normalized_query: str, lang: str = "pidgin") -> str | None:
        """Return cached answer or None if miss/expired."""
        key = self._make_key(normalized_query, lang)
        with self._lock:
            if key in self._cache:
                answer, ts = self._cache[key]
                if time.time() - ts < self._ttl:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return answer
                else:
                    # Expired — remove it
                    del self._cache[key]
            self._misses += 1
            return None

    def put(self, normalized_query: str, lang: str, answer: str) -> None:
        """Store an answer in the cache."""
        key = self._make_key(normalized_query, lang)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (answer, time.time())
            # Evict oldest if over capacity
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
            }

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
