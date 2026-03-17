from typing import Any, Optional
import logging
import time

import httpx

from app.common.logging.logger import log_event
from app.common.metrics.metrics import observe_provider_latency
from app.common.utils.retry import (
    RetryPolicy,
    RetrySignal,
    attach_retry_signal,
    run_with_retry,
)
from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import LLMBadResponseError, LLMTimeoutError
from app.ports.outbound.llm_client import LLMClientPort

logger = logging.getLogger(__name__)


class VLLMHTTPClient(LLMClientPort):
    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        connect_timeout_sec: float,
        read_timeout_sec: float,
        retry_count: int,
        retry_base_delay_sec: float,
        retry_max_delay_sec: float,
        retry_jitter_enabled: bool,
        retry_jitter_ratio: float,
        retry_total_timeout_sec: float,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._retry_policy = RetryPolicy(
            max_attempts=max(1, retry_count + 1),
            base_delay_sec=retry_base_delay_sec,
            max_delay_sec=retry_max_delay_sec,
            jitter_enabled=retry_jitter_enabled,
            jitter_ratio=retry_jitter_ratio,
            total_timeout_sec=retry_total_timeout_sec,
        )
        if http_client is None:
            timeout = httpx.Timeout(
                connect=connect_timeout_sec,
                read=read_timeout_sec,
                write=read_timeout_sec,
                pool=connect_timeout_sec,
            )
            self._client = httpx.AsyncClient(timeout=timeout)
            self._owns_client = True
        else:
            self._client = http_client
            self._owns_client = False

    async def generate(self, messages: list[ChatMessage]) -> str:
        payload = self._build_request_payload(messages)
        provider = "llm"
        operation = "generate"
        idempotent = True

        def _retry_logger(attempt: int, exc: Exception, delay: float) -> None:
            signal = getattr(exc, "_retry_signal", None)
            log_event(
                logger,
                logging.WARNING,
                "retry scheduled",
                provider=provider,
                path="/v1/chat/completions",
                status=getattr(signal, "error_code", None),
                result="retry",
                retry_attempt=attempt,
                retry_delay_ms=round(delay * 1000, 2),
                retry_reason=str(exc),
            )

        async def _request() -> str:
            started = time.perf_counter()
            try:
                response = await self._client.post(f"{self._base_url}/v1/chat/completions", json=payload)
            except httpx.ConnectTimeout as exc:
                duration = time.perf_counter() - started
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm connect timeout", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status="connect_timeout")
                err = LLMTimeoutError("llm provider connect timeout")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="timeout",
                        timeout_type="connect_timeout",
                    ),
                )
                raise err from exc
            except httpx.ReadTimeout as exc:
                duration = time.perf_counter() - started
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm read timeout", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status="read_timeout")
                err = LLMTimeoutError("llm provider read timeout")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="timeout",
                        timeout_type="read_timeout",
                    ),
                )
                raise err from exc
            except httpx.TimeoutException as exc:
                duration = time.perf_counter() - started
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm timeout", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status="total_timeout")
                err = LLMTimeoutError("llm provider total timeout")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="timeout",
                        timeout_type="total_timeout",
                    ),
                )
                raise err from exc
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                duration = time.perf_counter() - started
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm transient network error", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status="network_error")
                err = LLMBadResponseError("llm transient network error")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="network_error",
                    ),
                )
                raise err from exc
            except httpx.HTTPError as exc:
                duration = time.perf_counter() - started
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm call transport error", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status="error")
                err = LLMBadResponseError("llm transport error")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="transport_error",
                    ),
                )
                raise err from exc

            duration = time.perf_counter() - started
            if response.status_code >= 400:
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm call bad status", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status=str(response.status_code))
                err = LLMBadResponseError(f"llm status={response.status_code}")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="http_status",
                        http_status=response.status_code,
                    ),
                )
                raise err

            try:
                body = response.json()
            except ValueError as exc:
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "llm invalid json", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="failure", status="invalid_json")
                err = LLMBadResponseError("llm response is not valid json")
                attach_retry_signal(
                    err,
                    RetrySignal(
                        provider=provider,
                        operation=operation,
                        idempotent=idempotent,
                        error_code=err.error_code,
                        exception_type="invalid_json",
                    ),
                )
                raise err from exc

            content = self._parse_response_content(body)
            observe_provider_latency(provider, operation, "success", duration)
            log_event(logger, logging.INFO, "llm call success", provider=provider, path="/v1/chat/completions", latency_ms=round(duration * 1000, 2), result="success", status="ok")
            return content

        try:
            return await run_with_retry(
                operation=_request,
                policy=self._retry_policy,
                on_retry=_retry_logger,
            )
        except (LLMTimeoutError, LLMBadResponseError):
            raise
        except Exception as exc:
            raise LLMBadResponseError("llm generation failed") from exc

    def _build_request_payload(self, messages: list[ChatMessage]) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [m.model_dump() for m in messages],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }

    def _parse_response_content(self, body: dict[str, Any]) -> str:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMBadResponseError("llm response has no choices")

        first = choices[0]
        if not isinstance(first, dict):
            raise LLMBadResponseError("llm choice item is invalid")

        message = first.get("message")
        if not isinstance(message, dict):
            raise LLMBadResponseError("llm response has no message object")

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            err = LLMBadResponseError("llm response content is empty")
            attach_retry_signal(
                err,
                RetrySignal(
                    provider="llm",
                    operation="generate",
                    idempotent=True,
                    error_code=err.error_code,
                    exception_type="invalid_body",
                ),
            )
            raise err

        _usage = body.get("usage")
        return content

    async def ping(self) -> bool:
        started = time.perf_counter()
        try:
            response = await self._client.get(f"{self._base_url}/health")
            ok = response.status_code < 500
            duration = time.perf_counter() - started
            observe_provider_latency("llm", "ping", "success" if ok else "failure", duration)
            return ok
        except Exception:
            duration = time.perf_counter() - started
            observe_provider_latency("llm", "ping", "failure", duration)
            return False

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
