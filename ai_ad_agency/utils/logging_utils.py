"""
Structured logging utilities.
Provides console + file logging with rich formatting.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Rich is optional — fall back to plain logging if unavailable
try:
    from rich.console import Console
    from rich.logging import RichHandler
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

_loggers: dict[str, logging.Logger] = {}
_console: Optional[object] = None


def get_console() -> object:
    global _console
    if _console is None and _RICH_AVAILABLE:
        _console = Console(stderr=True)
    return _console


def get_logger(
    name: str = "ai_ad_agency",
    level: str = "INFO",
    log_dir: Optional[str] = None,
    log_to_file: bool = True,
) -> logging.Logger:
    """
    Return a cached logger. First call initializes handlers.
    Subsequent calls with the same name return the existing logger.
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    # Remove any default handlers
    logger.handlers.clear()

    # Console handler
    if _RICH_AVAILABLE:
        console_handler = RichHandler(
            console=get_console(),  # type: ignore[arg-type]
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.addHandler(console_handler)
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s  %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(fmt)
        logger.addHandler(console_handler)

    # File handler
    if log_to_file:
        if log_dir is None:
            log_dir = "ai_ad_agency/data/logs"
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d")
        log_file = Path(log_dir) / f"{name.replace('.', '_')}_{ts}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """Convenience wrapper — returns a child logger under 'ai_ad_agency'."""
    return logging.getLogger(f"ai_ad_agency.{module_name}")


def log_provider_call(
    logger: logging.Logger,
    provider: str,
    endpoint: str,
    payload_summary: str,
) -> None:
    logger.debug(
        "[PROVIDER CALL] %s → %s  payload=%s",
        provider,
        endpoint,
        payload_summary[:200],
    )


def log_provider_response(
    logger: logging.Logger,
    provider: str,
    endpoint: str,
    status: int | str,
    summary: str = "",
) -> None:
    logger.debug(
        "[PROVIDER RESP] %s ← %s  status=%s  %s",
        provider,
        endpoint,
        status,
        summary[:200],
    )


def log_retry(
    logger: logging.Logger,
    attempt: int,
    max_attempts: int,
    delay: float,
    reason: str,
) -> None:
    logger.warning(
        "[RETRY %d/%d] Waiting %.1fs. Reason: %s",
        attempt,
        max_attempts,
        delay,
        reason,
    )


def log_batch_summary(
    logger: logging.Logger,
    label: str,
    total: int,
    accepted: int,
    rejected: int,
) -> None:
    logger.info(
        "[BATCH SUMMARY] %s — total=%d  accepted=%d  rejected=%d",
        label,
        total,
        accepted,
        rejected,
    )
