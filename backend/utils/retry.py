"""
Retry utilities with exponential backoff.

Provides robust retry logic for handling transient failures
in API calls and network operations.
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Tuple, Type, Optional, Any, Union

logger = logging.getLogger('backend.utils.retry')


class RetryError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """Calculate exponential backoff delay.

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)

    if jitter:
        # Add random jitter (0-25% of delay)
        delay = delay * (1 + random.random() * 0.25)

    return delay


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    should_retry: Optional[Callable[[Exception], bool]] = None
) -> Callable:
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        max_delay: Maximum delay between retries
        exceptions: Tuple of exception types to retry on
        on_retry: Callback called on each retry (attempt, exception)
        should_retry: Function to determine if exception should be retried

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    # Check if we should retry this specific exception
                    if should_retry and not should_retry(e):
                        raise

                    # Don't retry on last attempt
                    if attempt == max_attempts - 1:
                        break

                    delay = exponential_backoff(attempt, base_delay, max_delay)

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(delay)

            # All attempts exhausted
            raise RetryError(
                f"All {max_attempts} attempts failed for {func.__name__}",
                last_exception
            )

        return wrapper
    return decorator


def retry_on_rate_limit(
    max_attempts: int = 5,
    base_delay: float = 60.0,
    rate_limit_exceptions: Tuple[Type[Exception], ...] = None
) -> Callable:
    """Specialized retry decorator for rate limit errors.

    Uses longer delays appropriate for rate limiting scenarios.

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Base delay (typically 60s for per-minute limits)
        rate_limit_exceptions: Exception types that indicate rate limiting

    Returns:
        Decorated function
    """
    from backend.dataflows.alpha_vantage_common import AlphaVantageRateLimitError

    if rate_limit_exceptions is None:
        rate_limit_exceptions = (AlphaVantageRateLimitError,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except rate_limit_exceptions as e:
                    if attempt == max_attempts - 1:
                        raise RetryError(
                            f"Rate limit exceeded after {max_attempts} attempts",
                            e
                        )

                    # Use fixed delay for rate limits (typically need to wait full window)
                    delay = base_delay * (1 + random.random() * 0.1)

                    logger.warning(
                        f"Rate limit hit for {func.__name__}. "
                        f"Waiting {delay:.0f}s before retry {attempt + 2}/{max_attempts}..."
                    )

                    time.sleep(delay)

        return wrapper
    return decorator


class RetryContext:
    """Context manager for retry logic with state tracking.

    Example:
        with RetryContext(max_attempts=3) as retry:
            for attempt in retry:
                try:
                    result = risky_operation()
                    break
                except SomeError as e:
                    retry.record_failure(e)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exceptions = exceptions

        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.success = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and isinstance(exc_val, self.exceptions):
            if self.attempt < self.max_attempts - 1:
                delay = exponential_backoff(self.attempt, self.base_delay, self.max_delay)
                logger.debug(f"Retry context: sleeping {delay:.2f}s before next attempt")
                time.sleep(delay)
                return True  # Suppress exception
        return False

    def __iter__(self):
        while self.attempt < self.max_attempts:
            yield self.attempt
            if self.success:
                break
            self.attempt += 1

    def record_failure(self, exception: Exception) -> None:
        """Record a failed attempt."""
        self.last_exception = exception

    def mark_success(self) -> None:
        """Mark the operation as successful."""
        self.success = True
