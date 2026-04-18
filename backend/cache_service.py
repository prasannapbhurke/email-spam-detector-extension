import hashlib
import json
from typing import Optional, Any
import redis
import os
from cachetools import TTLCache

class CacheService:
    def __init__(self):
        # Redis configuration (Railway provides REDIS_URL)
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = None
        
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                print("Redis cache initialized")
            except Exception as e:
                print(f"Redis connection failed: {e}. Falling back to in-memory.")

        # In-memory fallback
        self.local_cache = TTLCache(maxsize=1000, ttl=1800) # 30 min TTL

    def _get_key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[Any]:
        key = self._get_key(text)
        
        # Try Redis
        if self.redis_client:
            try:
                cached = self.redis_client.get(key)
                if cached: return json.loads(cached)
            except: pass
            
        # Try Memory
        return self.local_cache.get(key)

    def set(self, text: str, value: Any):
        key = self._get_key(text)
        
        # Set Memory
        self.local_cache[key] = value
        
        # Set Redis
        if self.redis_client:
            try:
                self.redis_client.setex(key, 1800, json.dumps(value))
            except: pass

cache_service = CacheService()
