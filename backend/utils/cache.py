"""
Simple disk-based cache using diskcache.
No Redis needed — runs entirely local and free.
"""

import logging
from pathlib import Path
import diskcache

logger = logging.getLogger(__name__)
CACHE_DIR = Path("data/cache")


class DiskCache:
    def __init__(self, ttl: int = 3600):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.cache = diskcache.Cache(str(CACHE_DIR))
        self.default_ttl = ttl

    def get(self, key: str):
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(self, key: str, value, ttl: int = None):
        try:
            self.cache.set(key, value, expire=ttl or self.default_ttl)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def delete(self, key: str):
        try:
            self.cache.delete(key)
        except Exception:
            pass

    def clear(self):
        try:
            self.cache.clear()
        except Exception:
            pass

    def size(self) -> int:
        try:
            return len(self.cache)
        except Exception:
            return 0
