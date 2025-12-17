"""
Backend utilities for rate limiting, caching, retry logic, and parallel execution.
"""

from .rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    rate_limited,
    get_all_limiter_stats,
    ALPHA_VANTAGE_LIMITER,
    FINNHUB_LIMITER,
    OPENAI_LIMITER,
    init_default_limiters,
)

from .retry import (
    RetryError,
    exponential_backoff,
    retry_with_backoff,
    retry_on_rate_limit,
    RetryContext,
)

from .cache import (
    LRUCache,
    RedisCache,
    get_llm_cache,
    get_data_cache,
    cached,
    cache_llm_response,
    get_cached_llm_response,
)

from .parallel import (
    fetch_parallel,
    fetch_parallel_async,
    batch_fetch,
    ParallelDataFetcher,
    get_executor,
)

__all__ = [
    # Rate limiting
    "RateLimiter",
    "get_rate_limiter",
    "rate_limited",
    "get_all_limiter_stats",
    "ALPHA_VANTAGE_LIMITER",
    "FINNHUB_LIMITER",
    "OPENAI_LIMITER",
    "init_default_limiters",
    # Retry
    "RetryError",
    "exponential_backoff",
    "retry_with_backoff",
    "retry_on_rate_limit",
    "RetryContext",
    # Cache
    "LRUCache",
    "RedisCache",
    "get_llm_cache",
    "get_data_cache",
    "cached",
    "cache_llm_response",
    "get_cached_llm_response",
    # Parallel
    "fetch_parallel",
    "fetch_parallel_async",
    "batch_fetch",
    "ParallelDataFetcher",
    "get_executor",
]
