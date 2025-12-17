"""
Caching utilities for LLM responses and data fetching.

Provides in-memory and Redis-backed caching with TTL support.
"""

import time
import hashlib
import json
import logging
import threading
from typing import Any, Optional, Callable, Dict, Union
from functools import wraps
from collections import OrderedDict

logger = logging.getLogger('backend.utils.cache')


class LRUCache:
    """Thread-safe LRU cache with TTL support.

    Uses OrderedDict for O(1) access and eviction.
    """

    def __init__(self, maxsize: int = 1000, ttl: Optional[float] = None):
        """Initialize LRU cache.

        Args:
            maxsize: Maximum number of items to cache
            ttl: Time-to-live in seconds (None = no expiration)
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()

        # Statistics
        self.hits = 0
        self.misses = 0

    def _make_key(self, *args, **kwargs) -> str:
        """Create a cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _is_expired(self, key: str) -> bool:
        """Check if a cache entry has expired."""
        if self.ttl is None:
            return False
        timestamp = self._timestamps.get(key, 0)
        return time.time() - timestamp > self.ttl

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.

        Returns None if key not found or expired.
        """
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            if self._is_expired(key):
                del self._cache[key]
                del self._timestamps[key]
                self.misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self.hits += 1
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set a value in cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    # Evict oldest
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    del self._timestamps[oldest_key]

            self._cache[key] = value
            self._timestamps[key] = time.time()

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(hit_rate, 3),
                "ttl": self.ttl,
            }


class RedisCache:
    """Redis-backed cache with TTL support.

    Falls back to in-memory cache if Redis is unavailable.
    """

    def __init__(
        self,
        prefix: str = "tradingagents",
        ttl: int = 3600,
        fallback_cache: Optional[LRUCache] = None
    ):
        """Initialize Redis cache.

        Args:
            prefix: Key prefix for namespacing
            ttl: Default TTL in seconds
            fallback_cache: LRU cache to use if Redis unavailable
        """
        self.prefix = prefix
        self.ttl = ttl
        self.fallback_cache = fallback_cache or LRUCache(maxsize=500, ttl=ttl)
        self._redis = None
        self._redis_available = False
        self._init_redis()

    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis
            import os

            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))

            self._redis = redis.Redis(host=host, port=port, decode_responses=True)
            self._redis.ping()
            self._redis_available = True
            logger.info(f"Redis cache initialized at {host}:{port}")

        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            self._redis_available = False

    def _full_key(self, key: str) -> str:
        """Create full Redis key with prefix."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if self._redis_available:
            try:
                value = self._redis.get(self._full_key(key))
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.warning(f"Redis get error, falling back: {e}")

        return self.fallback_cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache."""
        ttl = ttl or self.ttl

        if self._redis_available:
            try:
                self._redis.setex(
                    self._full_key(key),
                    ttl,
                    json.dumps(value, default=str)
                )
                return
            except Exception as e:
                logger.warning(f"Redis set error, falling back: {e}")

        self.fallback_cache.set(key, value)

    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        if self._redis_available:
            try:
                self._redis.delete(self._full_key(key))
            except Exception:
                pass

        # Also clear from fallback
        with self.fallback_cache._lock:
            if key in self.fallback_cache._cache:
                del self.fallback_cache._cache[key]


# Global caches
_llm_cache: Optional[LRUCache] = None
_data_cache: Optional[RedisCache] = None


def get_llm_cache(maxsize: int = 500, ttl: float = 3600) -> LRUCache:
    """Get or create the LLM response cache."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LRUCache(maxsize=maxsize, ttl=ttl)
    return _llm_cache


def get_data_cache(prefix: str = "tradingagents", ttl: int = 3600) -> RedisCache:
    """Get or create the data cache."""
    global _data_cache
    if _data_cache is None:
        _data_cache = RedisCache(prefix=prefix, ttl=ttl)
    return _data_cache


def cached(
    cache: Optional[Union[LRUCache, RedisCache]] = None,
    ttl: Optional[float] = None,
    key_prefix: str = ""
) -> Callable:
    """Decorator to cache function results.

    Args:
        cache: Cache instance to use (defaults to LLM cache)
        ttl: TTL override for this function
        key_prefix: Prefix for cache keys

    Returns:
        Decorated function

    Example:
        @cached(ttl=3600)
        def expensive_llm_call(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal cache
            if cache is None:
                cache = get_llm_cache()

            # Create cache key
            key_data = {
                "func": func.__name__,
                "prefix": key_prefix,
                "args": args,
                "kwargs": kwargs
            }
            key = hashlib.sha256(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]

            # Check cache
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            if isinstance(cache, RedisCache) and ttl:
                cache.set(key, result, ttl=int(ttl))
            else:
                cache.set(key, result)

            return result

        return wrapper
    return decorator


def cache_llm_response(
    prompt_hash: str,
    response: str,
    model: str = "unknown",
    ttl: int = 3600
) -> None:
    """Cache an LLM response.

    Args:
        prompt_hash: Hash of the prompt
        response: LLM response text
        model: Model identifier
        ttl: Time-to-live in seconds
    """
    cache = get_llm_cache()
    key = f"llm:{model}:{prompt_hash}"
    cache.set(key, response)


def get_cached_llm_response(
    prompt_hash: str,
    model: str = "unknown"
) -> Optional[str]:
    """Get a cached LLM response.

    Args:
        prompt_hash: Hash of the prompt
        model: Model identifier

    Returns:
        Cached response or None
    """
    cache = get_llm_cache()
    key = f"llm:{model}:{prompt_hash}"
    return cache.get(key)
