#!/usr/bin/env python3
"""Retry utilities for Kimi Code CLI agent operations.

Kimi API can return transient errors such as 502/504 or time out under load.
This module provides a small decorator that retries operations with
exponential backoff and logs each attempt.
"""

from __future__ import annotations

import functools
import subprocess
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class KimiTransientError(Exception):
    """Raised when an operation fails after all retry attempts."""


# Patterns that indicate a transient Kimi/platform error worth retrying.
_TRANSIENT_SUBSTRINGS = (
    "502",
    "504",
    "Bad Gateway",
    "Gateway Timeout",
    "timeout",
    "Temporary failure",
    "Connection reset",
    "Connection refused",
)


def _is_transient_error(exc: BaseException) -> bool:
    """Return True if the exception looks like a transient platform error."""
    text = ""
    if isinstance(exc, subprocess.CalledProcessError):
        text = f"{exc.stderr or ''}\n{exc.stdout or ''}"
    else:
        text = str(exc)
    lower = text.lower()
    return any(sub.lower() in lower for sub in _TRANSIENT_SUBSTRINGS)


def retry_on_kimi_errors(
    max_attempts: int = 4,
    backoff_seconds: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a function on transient Kimi/platform errors.

    Args:
        max_attempts: Maximum number of attempts (must be >= 1).
            Default 4 gives backoff delays 2s, 4s, 8s across retries.
        backoff_seconds: Initial backoff between attempts, doubled each time.

    Raises:
        KimiTransientError: If all attempts fail with a transient error.
        The original exception is re-raised if the first failure is not transient.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            last_exception: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt == 1 and not _is_transient_error(exc):
                        raise
                    if attempt == max_attempts:
                        break
                    if not _is_transient_error(exc):
                        raise
                    sleep_time = backoff_seconds * (2 ** (attempt - 1))
                    print(
                        f"Transient error on attempt {attempt}/{max_attempts}: {exc}. "
                        f"Retrying in {sleep_time}s...",
                        file=sys.stderr,
                    )
                    time.sleep(sleep_time)

            raise KimiTransientError(
                f"Operation failed after {max_attempts} attempts: {last_exception}"
            ) from last_exception

        return wrapper

    return decorator


import sys  # noqa: E402


if __name__ == "__main__":
    # Simple self-test: a function that fails twice with 502 then succeeds.
    _counter = 0

    @retry_on_kimi_errors(max_attempts=4, backoff_seconds=0.1)
    def _flaky() -> str:
        global _counter
        _counter += 1
        if _counter < 4:
            raise RuntimeError("502 Bad Gateway from Kimi API")
        return "success"

    print(_flaky())
