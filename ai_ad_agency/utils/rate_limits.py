"""
Token-bucket rate limiter for provider API calls.
Thread-safe, supports per-provider limits.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict

import logging

logger = logging.getLogger("ai_ad_agency.rate_limits")


@dataclass
class RateLimiter:
    """
    Simple token-bucket rate limiter.
    Blocks the calling thread until a token is available.
    """
    requests_per_minute: int
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.requests_per_minute)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self.requests_per_minute / 60.0)
        self._tokens = min(self.requests_per_minute, self._tokens + new_tokens)
        self._last_refill = now

    def acquire(self, tokens: float = 1.0) -> None:
        """Block until `tokens` tokens are available."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                # Calculate how long to wait
                deficit = tokens - self._tokens
                wait_sec = deficit / (self.requests_per_minute / 60.0)

            logger.debug("[RATE LIMIT] Waiting %.2fs for token", wait_sec)
            time.sleep(min(wait_sec, 1.0))

    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Non-blocking acquire. Returns True if successful."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False


# Global registry of rate limiters keyed by provider name
_limiters: Dict[str, RateLimiter] = {}
_registry_lock = threading.Lock()


def get_limiter(provider: str, requests_per_minute: int = 60) -> RateLimiter:
    """
    Get or create a rate limiter for the given provider.
    Thread-safe singleton per provider name.
    """
    with _registry_lock:
        if provider not in _limiters:
            _limiters[provider] = RateLimiter(requests_per_minute=requests_per_minute)
            logger.debug(
                "[RATE LIMIT] Created limiter for %s @ %d RPM",
                provider,
                requests_per_minute,
            )
        return _limiters[provider]


def configure_limiter(provider: str, requests_per_minute: int) -> None:
    """Override or create a rate limiter for a provider."""
    with _registry_lock:
        _limiters[provider] = RateLimiter(requests_per_minute=requests_per_minute)
        logger.info(
            "[RATE LIMIT] Configured %s @ %d RPM", provider, requests_per_minute
        )
