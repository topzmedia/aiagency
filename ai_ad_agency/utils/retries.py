"""
Retry utilities using tenacity.
Provides exponential backoff with jitter for all provider calls.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type

try:
    from tenacity import (
        RetryError,
        Retrying,
        before_sleep_log,
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
        wait_random_exponential,
    )
    _TENACITY = True
except ImportError:
    _TENACITY = False

logger = logging.getLogger("ai_ad_agency.retries")


class TransientError(Exception):
    """Raised for errors that should be retried."""


class FatalError(Exception):
    """Raised for errors that should NOT be retried."""


class ProviderRateLimitError(TransientError):
    """Raised when a provider returns 429 or similar."""


class ProviderTimeoutError(TransientError):
    """Raised when a provider times out."""


def with_retries(
    fn: Callable,
    *args: Any,
    max_attempts: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    reraise: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (TransientError, ProviderRateLimitError, ProviderTimeoutError),
    **kwargs: Any,
) -> Any:
    """
    Synchronous retry wrapper with exponential backoff.
    Falls back to manual loop if tenacity is unavailable.
    """
    if _TENACITY:
        retryer = Retrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_random_exponential(multiplier=base_delay, max=max_delay),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=reraise,
        )
        return retryer(fn, *args, **kwargs)
    else:
        # Manual fallback
        last_exc: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                return fn(*args, **kwargs)
            except retryable_exceptions as exc:
                last_exc = exc
                if attempt < max_attempts:
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "[RETRY %d/%d] %.1fs backoff. Error: %s",
                        attempt,
                        max_attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        if reraise and last_exc:
            raise last_exc
        return None


async def with_retries_async(
    fn: Callable,
    *args: Any,
    max_attempts: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (TransientError, ProviderRateLimitError, ProviderTimeoutError),
    **kwargs: Any,
) -> Any:
    """Async retry wrapper with exponential backoff."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt < max_attempts:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                logger.warning(
                    "[ASYNC RETRY %d/%d] %.1fs backoff. Error: %s",
                    attempt,
                    max_attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


def retry_decorator(
    max_attempts: int = 4,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (TransientError,),
) -> Callable:
    """
    Decorator factory for sync functions.
    Usage:
        @retry_decorator(max_attempts=3)
        def call_api(...): ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return with_retries(
                fn,
                *args,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                **kwargs,
            )
        return wrapper
    return decorator


def poll_until_complete(
    poll_fn: Callable[[], Any],
    is_done_fn: Callable[[Any], bool],
    is_failed_fn: Callable[[Any], bool],
    interval_sec: float = 10.0,
    max_attempts: int = 60,
    label: str = "job",
) -> Any:
    """
    Synchronously poll a remote job until it completes or fails.

    Args:
        poll_fn: Callable that fetches current status. Must not raise on retryable errors.
        is_done_fn: Returns True when job is complete.
        is_failed_fn: Returns True when job has permanently failed.
        interval_sec: Seconds between polls.
        max_attempts: Maximum poll attempts before raising ProviderTimeoutError.
        label: Human-readable label for logging.

    Returns:
        Last response from poll_fn when done.
    """
    for attempt in range(1, max_attempts + 1):
        result = poll_fn()
        if is_done_fn(result):
            logger.info("[POLL] %s completed after %d polls", label, attempt)
            return result
        if is_failed_fn(result):
            raise FatalError(f"{label} failed permanently. Last status: {result}")
        if attempt % 6 == 0:
            logger.info("[POLL] %s still processing... (%d/%d)", label, attempt, max_attempts)
        time.sleep(interval_sec)
    raise ProviderTimeoutError(
        f"{label} did not complete within {max_attempts * interval_sec:.0f}s"
    )
