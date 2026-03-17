from __future__ import annotations

import asyncio
import pytest

from app.common.utils.retry import (
    RetryPolicy,
    RetrySignal,
    attach_retry_signal,
    run_with_retry,
    should_retry_by_taxonomy,
)


class DummyRetryError(Exception):
    pass


@pytest.mark.asyncio
async def test_run_with_retry_respects_attempt_limit() -> None:
    calls = {"count": 0}

    async def operation() -> str:
        calls["count"] += 1
        err = DummyRetryError("temporary")
        attach_retry_signal(
            err,
            RetrySignal(
                provider="llm",
                operation="generate",
                idempotent=True,
                error_code="LLM_TIMEOUT",
                exception_type="timeout",
                timeout_type="read_timeout",
            ),
        )
        raise err

    with pytest.raises(DummyRetryError):
        await run_with_retry(
            operation=operation,
            policy=RetryPolicy(
                max_attempts=3,
                base_delay_sec=0.0,
                max_delay_sec=0.0,
                jitter_enabled=False,
                jitter_ratio=0.0,
                total_timeout_sec=5.0,
            ),
        )

    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_backoff_and_jitter_are_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr("app.common.utils.retry.random.uniform", lambda low, high: high)

    async def operation() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            err = DummyRetryError("retry")
            attach_retry_signal(
                err,
                RetrySignal(
                    provider="llm",
                    operation="generate",
                    idempotent=True,
                    error_code="LLM_TIMEOUT",
                    exception_type="timeout",
                    timeout_type="read_timeout",
                ),
            )
            raise err
        return "ok"

    result = await run_with_retry(
        operation=operation,
        policy=RetryPolicy(
            max_attempts=3,
            base_delay_sec=0.2,
            max_delay_sec=0.4,
            jitter_enabled=True,
            jitter_ratio=0.5,
            total_timeout_sec=5.0,
        ),
    )

    assert result == "ok"
    assert sleeps == pytest.approx([0.3, 0.6], rel=1e-6, abs=1e-9)


@pytest.mark.asyncio
async def test_non_retryable_4xx_fails_immediately() -> None:
    calls = {"count": 0}

    async def operation() -> str:
        calls["count"] += 1
        err = DummyRetryError("bad request")
        attach_retry_signal(
            err,
            RetrySignal(
                provider="llm",
                operation="generate",
                idempotent=True,
                error_code="LLM_BAD_RESPONSE",
                exception_type="http_status",
                http_status=400,
            ),
        )
        raise err

    with pytest.raises(DummyRetryError):
        await run_with_retry(
            operation=operation,
            policy=RetryPolicy(
                max_attempts=4,
                base_delay_sec=0.0,
                max_delay_sec=0.0,
                jitter_enabled=False,
                jitter_ratio=0.0,
                total_timeout_sec=5.0,
            ),
        )

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_retry_budget_prevents_excessive_delay() -> None:
    calls = {"count": 0}

    async def operation() -> str:
        calls["count"] += 1
        err = DummyRetryError("timeout")
        attach_retry_signal(
            err,
            RetrySignal(
                provider="llm",
                operation="generate",
                idempotent=True,
                error_code="LLM_TIMEOUT",
                exception_type="timeout",
                timeout_type="read_timeout",
            ),
        )
        raise err

    with pytest.raises(DummyRetryError):
        await run_with_retry(
            operation=operation,
            policy=RetryPolicy(
                max_attempts=5,
                base_delay_sec=0.4,
                max_delay_sec=0.4,
                jitter_enabled=False,
                jitter_ratio=0.0,
                total_timeout_sec=0.1,
            ),
        )

    assert calls["count"] == 1


def test_should_retry_by_taxonomy_matrix_basics() -> None:
    retryable_429 = DummyRetryError("429")
    attach_retry_signal(
        retryable_429,
        RetrySignal(
            provider="llm",
            operation="generate",
            idempotent=True,
            error_code="LLM_BAD_RESPONSE",
            exception_type="http_status",
            http_status=429,
        ),
    )
    assert should_retry_by_taxonomy(retryable_429) is True

    non_retryable_invalid = DummyRetryError("invalid body")
    attach_retry_signal(
        non_retryable_invalid,
        RetrySignal(
            provider="tts",
            operation="synthesize",
            idempotent=False,
            error_code="TTS_BAD_RESPONSE",
            exception_type="invalid_body",
        ),
    )
    assert should_retry_by_taxonomy(non_retryable_invalid) is False
