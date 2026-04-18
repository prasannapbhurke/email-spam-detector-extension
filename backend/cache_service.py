import hashlib
import json
import os
import time
from typing import Optional, Any

try:
    import redis
except ImportError:
    redis = None

try:
    from cachetools import TTLCache
except ImportError:
    TTLCache = None


class SimpleTTLCache:
    def __init__(self, maxsize: int = 1000, ttl: int = 1800):
        self.maxsize = maxsize
        self.ttl = ttl
        self._store = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._store.get(key)
        if not item:
            return None

        expires_at, value = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None

        return value

    def __setitem__(self, key: str, value: Any):
        if len(self._store) >= self.maxsize:
            oldest_key = next(iter(self._store))
            self._store.pop(oldest_key, None)

        self._store[key] = (time.time() + self.ttl, value)


class CacheService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = None

        if self.redis_url and redis is not None:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                print("Redis cache initialized")
            except Exception as error:
                print(f"Redis connection failed: {error}. Falling back to in-memory.")

        if TTLCache is not None:
            self.local_cache = TTLCache(maxsize=1000, ttl=1800)
        else:
            self.local_cache = SimpleTTLCache(maxsize=1000, ttl=1800)

    def _get_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[Any]:
        key = self._get_key(text)

        if self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        return self.local_cache.get(key)

    def set(self, text: str, value: Any):
        key = self._get_key(text)
        self.local_cache[key] = value

        if self.redis_client:
            try:
                self.redis_client.setex(key, 1800, json.dumps(value))
            except Exception:
                pass


cache_service = CacheService()
