from __future__ import annotations

import asyncio
from dataclasses import dataclass
import random
import time
from typing import Awaitable, Callable, Literal, TypeVar

T = TypeVar("T")


TimeoutType = Literal[
    "connect_timeout",
    "read_timeout",
    "write_timeout",
    "pool_timeout",
    "total_timeout",
]


@dataclass(frozen=True)
class RetrySignal:
    provider: str
    operation: str
    idempotent: bool
    error_code: str
    exception_type: str
    http_status: int | None = None
    timeout_type: TimeoutType | None = None
    retryable_override: bool | None = None


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_delay_sec: float
    max_delay_sec: float
    jitter_enabled: bool
    jitter_ratio: float
    total_timeout_sec: float


def attach_retry_signal(exc: Exception, signal: RetrySignal) -> Exception:
    setattr(exc, "_retry_signal", signal)
    return exc


def extract_retry_signal(exc: Exception) -> RetrySignal | None:
    signal = getattr(exc, "_retry_signal", None)
    if isinstance(signal, RetrySignal):
        return signal
    return None


def should_retry_by_taxonomy(exc: Exception) -> bool:
    signal = extract_retry_signal(exc)
    if signal is None:
        return False
    if signal.retryable_override is not None:
        return signal.retryable_override

    if signal.http_status == 429:
        return True

    if signal.http_status in {500, 502, 503, 504}:
        return signal.idempotent

    if signal.http_status is not None and 400 <= signal.http_status < 500:
        return False

    if signal.timeout_type == "connect_timeout":
        return True

    if signal.timeout_type in {"read_timeout", "write_timeout", "pool_timeout", "total_timeout"}:
        return signal.idempotent

    if signal.exception_type in {"connect_error", "network_error", "connection_reset"}:
        return signal.idempotent

    if signal.exception_type in {"invalid_json", "invalid_body", "semantic_error"}:
        return False

    if signal.error_code in {"LLM_TIMEOUT", "TTS_TIMEOUT"}:
        return signal.idempotent

    return False


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    should_retry: Callable[[Exception], bool] = should_retry_by_taxonomy,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    started = time.monotonic()
    max_attempts = max(1, policy.max_attempts)

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_attempts or not should_retry(exc):
                raise

            exponent = max(0, attempt - 1)
            delay = min(policy.max_delay_sec, policy.base_delay_sec * (2**exponent))
            if policy.jitter_enabled:
                jitter_upper = max(0.0, delay * max(0.0, policy.jitter_ratio))
                delay += random.uniform(0.0, jitter_upper)

            elapsed = time.monotonic() - started
            if elapsed + delay > policy.total_timeout_sec:
                raise

            if on_retry is not None:
                on_retry(attempt, exc, delay)
            await asyncio.sleep(delay)
