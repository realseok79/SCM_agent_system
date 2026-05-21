import os
import json
import time
import threading
import logging
from typing import Any, Optional

logger = logging.getLogger("FeatureStore")

class InMemoryFeatureStore:
    """
    A thread-safe in-memory key-value store with TTL expiration support.
    Used as a fallback when Redis is unavailable.
    """
    def __init__(self):
        self._store = {}
        self._expires = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        with self._lock:
            self._store[key] = value
            if expire_seconds is not None:
                self._expires[key] = time.time() + expire_seconds
            else:
                self._expires.pop(key, None)
            return True

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            # Check expiration
            if key in self._expires:
                if time.time() > self._expires[key]:
                    # Expired
                    self._store.pop(key, None)
                    self._expires.pop(key, None)
                    return None
            return self._store.get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            self._store.pop(key, None)
            self._expires.pop(key, None)
            return True


class FeatureStore:
    """
    Unified Feature Store interface for caching SCM parameters, GDELT risks, Weather scores, etc.
    Tries Redis first, falls back to In-Memory store if Redis is unavailable.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(FeatureStore, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_client = None
        self.fallback_store = InMemoryFeatureStore()
        
        # Try to connect to Redis
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("🔌 Successfully connected to Redis Feature Store.")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed ({e}). Falling back to thread-safe In-Memory Feature Store.")
            self.redis_client = None

        self._initialized = True

    def set_feature(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """
        Store a feature value under a key. Value is automatically serialized to JSON.
        """
        serialized = json.dumps(value)
        if self.redis_client:
            try:
                if expire_seconds:
                    self.redis_client.set(key, serialized, ex=expire_seconds)
                else:
                    self.redis_client.set(key, serialized)
                return True
            except Exception as e:
                logger.error(f"❌ Redis set failed ({e}). Attempting fallback storage.")
                self.redis_client = None # Degrade to fallback
                
        return self.fallback_store.set(key, value, expire_seconds)

    def get_feature(self, key: str) -> Optional[Any]:
        """
        Retrieve a feature value by key. Decodes JSON back to original python objects.
        """
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val is not None:
                    return json.loads(val)
                return None
            except Exception as e:
                logger.error(f"❌ Redis get failed ({e}). Attempting fallback read.")
                self.redis_client = None # Degrade to fallback
                
        return self.fallback_store.get(key)

    def delete_feature(self, key: str) -> bool:
        """
        Delete a feature key from the store.
        """
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"❌ Redis delete failed ({e}). Attempting fallback delete.")
                self.redis_client = None
                
        return self.fallback_store.delete(key)

# Global Singleton Instance
feature_store = FeatureStore(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", None)
)
