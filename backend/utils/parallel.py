"""
Parallel data fetching utilities using asyncio.

Provides concurrent execution for independent data fetches
to reduce total latency when multiple data sources are needed.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Any, List, Tuple, Optional
from functools import partial

logger = logging.getLogger('backend.utils.parallel')

# Thread pool for running sync functions concurrently
_executor: Optional[ThreadPoolExecutor] = None


def get_executor(max_workers: int = 10) -> ThreadPoolExecutor:
    """Get or create the global thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=max_workers)
    return _executor


def fetch_parallel(
    tasks: Dict[str, Callable[[], Any]],
    timeout: float = 30.0,
    fail_fast: bool = False
) -> Dict[str, Any]:
    """Execute multiple data fetching tasks in parallel.

    Args:
        tasks: Dictionary mapping task names to callables
        timeout: Maximum time to wait for all tasks
        fail_fast: If True, raise on first error; if False, collect all results

    Returns:
        Dictionary mapping task names to results (or exceptions if fail_fast=False)

    Example:
        results = fetch_parallel({
            "stock_data": lambda: get_stock_data("AAPL", "2024-01-01", "2024-12-01"),
            "indicators": lambda: get_indicators("AAPL", "RSI", "2024-12-01"),
            "news": lambda: get_news("AAPL", "2024-11-01", "2024-12-01"),
        })
    """
    if not tasks:
        return {}

    results = {}
    executor = get_executor()

    # Submit all tasks
    future_to_name = {
        executor.submit(func): name
        for name, func in tasks.items()
    }

    # Collect results
    for future in as_completed(future_to_name, timeout=timeout):
        name = future_to_name[future]
        try:
            results[name] = future.result()
            logger.debug(f"Task '{name}' completed successfully")
        except Exception as e:
            logger.warning(f"Task '{name}' failed: {e}")
            if fail_fast:
                raise
            results[name] = e

    return results


async def fetch_parallel_async(
    tasks: Dict[str, Callable[[], Any]],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Async version of parallel fetch using asyncio.

    Wraps synchronous callables in asyncio.to_thread for concurrent execution.

    Args:
        tasks: Dictionary mapping task names to callables
        timeout: Maximum time to wait for all tasks

    Returns:
        Dictionary mapping task names to results
    """
    if not tasks:
        return {}

    async def run_task(name: str, func: Callable) -> Tuple[str, Any]:
        try:
            result = await asyncio.to_thread(func)
            return name, result
        except Exception as e:
            logger.warning(f"Async task '{name}' failed: {e}")
            return name, e

    # Create all tasks
    async_tasks = [run_task(name, func) for name, func in tasks.items()]

    # Run with timeout
    try:
        completed = await asyncio.wait_for(
            asyncio.gather(*async_tasks, return_exceptions=True),
            timeout=timeout
        )
        return dict(completed)
    except asyncio.TimeoutError:
        logger.error(f"Parallel fetch timed out after {timeout}s")
        raise


def batch_fetch(
    items: List[Any],
    fetch_func: Callable[[Any], Any],
    batch_size: int = 5,
    delay_between_batches: float = 0.0
) -> List[Any]:
    """Fetch items in batches with optional delay between batches.

    Useful for rate-limited APIs where you want parallelism within
    rate limit constraints.

    Args:
        items: List of items to fetch
        fetch_func: Function to apply to each item
        batch_size: Number of items per batch
        delay_between_batches: Delay in seconds between batches

    Returns:
        List of results in same order as input items
    """
    import time

    results = [None] * len(items)
    executor = get_executor()

    for batch_start in range(0, len(items), batch_size):
        batch_end = min(batch_start + batch_size, len(items))
        batch_items = items[batch_start:batch_end]

        # Submit batch
        futures = {
            executor.submit(fetch_func, item): idx
            for idx, item in enumerate(batch_items, start=batch_start)
        }

        # Collect batch results
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.warning(f"Batch item {idx} failed: {e}")
                results[idx] = e

        # Delay before next batch (if not last batch)
        if batch_end < len(items) and delay_between_batches > 0:
            time.sleep(delay_between_batches)

    return results


class ParallelDataFetcher:
    """Helper class for building and executing parallel data fetches.

    Example:
        fetcher = ParallelDataFetcher()
        fetcher.add("stock", get_stock_data, "AAPL", "2024-01-01", "2024-12-01")
        fetcher.add("news", get_news, "AAPL", "2024-11-01", "2024-12-01")
        results = fetcher.execute()
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.tasks: Dict[str, Callable[[], Any]] = {}

    def add(self, name: str, func: Callable, *args, **kwargs) -> "ParallelDataFetcher":
        """Add a task to the fetcher.

        Args:
            name: Unique name for this task
            func: Function to call
            *args, **kwargs: Arguments to pass to function

        Returns:
            Self for chaining
        """
        self.tasks[name] = partial(func, *args, **kwargs)
        return self

    def execute(self, fail_fast: bool = False) -> Dict[str, Any]:
        """Execute all tasks in parallel.

        Args:
            fail_fast: If True, raise on first error

        Returns:
            Dictionary mapping task names to results
        """
        return fetch_parallel(self.tasks, timeout=self.timeout, fail_fast=fail_fast)

    async def execute_async(self) -> Dict[str, Any]:
        """Execute all tasks asynchronously."""
        return await fetch_parallel_async(self.tasks, timeout=self.timeout)

    def clear(self) -> "ParallelDataFetcher":
        """Clear all tasks."""
        self.tasks.clear()
        return self
