"""
Rate limiting and request queuing utilities for API calls.

Provides token bucket rate limiting with automatic queuing for
APIs with strict rate limits (e.g., Alpha Vantage: 5 calls/min).
"""

import time
import threading
import logging
from collections import deque
from functools import wraps
from typing import Callable, Dict, Any, Optional

logger = logging.getLogger('backend.utils.rate_limiter')


class RateLimiter:
    """Token bucket rate limiter with request queuing.

    Implements a token bucket algorithm that:
    - Allows burst requests up to bucket capacity
    - Refills tokens at a steady rate
    - Queues requests when rate limit is reached
    """

    def __init__(
        self,
        calls_per_minute: int = 5,
        burst_size: Optional[int] = None,
        name: str = "default"
    ):
        """Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute
            burst_size: Maximum burst size (defaults to calls_per_minute)
            name: Identifier for logging
        """
        self.calls_per_minute = calls_per_minute
        self.burst_size = burst_size or calls_per_minute
        self.name = name

        # Token bucket state
        self.tokens = float(self.burst_size)
        self.last_refill = time.monotonic()
        self.refill_rate = calls_per_minute / 60.0  # tokens per second

        # Thread safety
        self._lock = threading.Lock()

        # Statistics
        self.total_calls = 0
        self.queued_calls = 0
        self.total_wait_time = 0.0

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst_size, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire a token, waiting if necessary.

        Args:
            timeout: Maximum time to wait (None = wait indefinitely)

        Returns:
            True if token acquired, False if timeout
        """
        start_time = time.monotonic()

        with self._lock:
            self._refill_tokens()

            if self.tokens >= 1:
                self.tokens -= 1
                self.total_calls += 1
                return True

            # Calculate wait time
            wait_time = (1 - self.tokens) / self.refill_rate

            if timeout is not None and wait_time > timeout:
                return False

            self.queued_calls += 1
            logger.debug(f"[{self.name}] Rate limit reached, waiting {wait_time:.2f}s")

        # Wait outside the lock
        time.sleep(wait_time)

        with self._lock:
            self._refill_tokens()
            self.tokens -= 1
            self.total_calls += 1
            self.total_wait_time += time.monotonic() - start_time

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self._lock:
            return {
                "name": self.name,
                "total_calls": self.total_calls,
                "queued_calls": self.queued_calls,
                "total_wait_time": round(self.total_wait_time, 2),
                "avg_wait_time": round(self.total_wait_time / max(1, self.queued_calls), 2),
                "current_tokens": round(self.tokens, 2),
            }


# Global rate limiters for different APIs
_rate_limiters: Dict[str, RateLimiter] = {}
_limiter_lock = threading.Lock()


def get_rate_limiter(
    name: str,
    calls_per_minute: int = 5,
    burst_size: Optional[int] = None
) -> RateLimiter:
    """Get or create a named rate limiter.

    Args:
        name: Unique name for this rate limiter
        calls_per_minute: Rate limit (only used on creation)
        burst_size: Burst size (only used on creation)

    Returns:
        RateLimiter instance
    """
    with _limiter_lock:
        if name not in _rate_limiters:
            _rate_limiters[name] = RateLimiter(
                calls_per_minute=calls_per_minute,
                burst_size=burst_size,
                name=name
            )
        return _rate_limiters[name]


def rate_limited(
    limiter_name: str,
    calls_per_minute: int = 5,
    timeout: Optional[float] = None
) -> Callable:
    """Decorator to apply rate limiting to a function.

    Args:
        limiter_name: Name of the rate limiter to use
        calls_per_minute: Rate limit (only used on first call)
        timeout: Maximum wait time before raising exception

    Returns:
        Decorated function

    Example:
        @rate_limited("alpha_vantage", calls_per_minute=5)
        def fetch_stock_data(symbol):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(limiter_name, calls_per_minute)

            if not limiter.acquire(timeout=timeout):
                raise TimeoutError(
                    f"Rate limiter '{limiter_name}' timeout after {timeout}s"
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator


# Pre-configured rate limiters for known APIs
ALPHA_VANTAGE_LIMITER = "alpha_vantage"  # 5 calls/min free tier
FINNHUB_LIMITER = "finnhub"  # 60 calls/min
OPENAI_LIMITER = "openai"  # Varies by tier


def init_default_limiters():
    """Initialize rate limiters with default configurations."""
    get_rate_limiter(ALPHA_VANTAGE_LIMITER, calls_per_minute=5)
    get_rate_limiter(FINNHUB_LIMITER, calls_per_minute=60)
    get_rate_limiter(OPENAI_LIMITER, calls_per_minute=60)


def get_all_limiter_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all rate limiters."""
    with _limiter_lock:
        return {name: limiter.get_stats() for name, limiter in _rate_limiters.items()}
