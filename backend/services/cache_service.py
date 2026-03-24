"""
============================================================
Cache Service – In-Memory TTL Cache
============================================================
Provides instant answers for repeated questions.
Thread-safe for single-worker Render deployments.

Usage:
    from backend.services.cache_service import cache
    cache.set(key, value, ttl=3600)
    value = cache.get(key)   # returns None if expired or missing
    cache.clear()
============================================================
"""

import time
import threading
import logging
from typing import Any, Optional

logger = logging.getLogger("botzi.cache")


class TTLCache:
    """Simple in-memory dictionary cache with per-key TTL."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Store value with expiry = now + ttl seconds."""
        expires_at = time.time() + ttl
        with self._lock:
            self._store[key] = (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        """Return value if present and not expired, else None."""
        with self._lock:
            entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            self.delete(key)
            return None
        return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
        logger.info("Cache cleared")

    def size(self) -> int:
        """Number of keys currently in cache (including expired)."""
        with self._lock:
            return len(self._store)

    def purge_expired(self) -> int:
        """Remove all expired keys. Returns count removed."""
        now = time.time()
        expired_keys = []
        with self._lock:
            for key, (_, expires_at) in list(self._store.items()):
                if now > expires_at:
                    expired_keys.append(key)
            for key in expired_keys:
                del self._store[key]
        if expired_keys:
            logger.info(f"Purged {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    def stats(self) -> dict:
        now = time.time()
        with self._lock:
            total = len(self._store)
            expired = sum(1 for _, exp in self._store.values() if now > exp)
        return {
            "total_keys": total,
            "active_keys": total - expired,
            "expired_keys": expired,
        }


# ── Module-level singleton ────────────────────────────────
cache = TTLCache()
