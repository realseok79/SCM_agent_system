# utils/db/cache.py
import os
import time
import json

class IdempotencyCache:
    def __init__(self):
        self.redis_client = None
        self.local_cache = {}  # Fallback in-memory dict: {key: (value, expire_time)}
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
        except Exception:
            pass

    def get(self, key):
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                return json.loads(val) if val else None
            except Exception:
                pass
        if key in self.local_cache:
            val, expire = self.local_cache[key]
            if time.time() < expire:
                return val
            else:
                del self.local_cache[key]
        return None

    def set(self, key, value, ttl=86400): # Default 24 hours
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass
        self.local_cache[key] = (value, time.time() + ttl)

idempotency_cache = IdempotencyCache()
