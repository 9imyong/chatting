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
from app.domain.exceptions.errors import TTSBadResponseError, TTSTimeoutError
from app.ports.outbound.tts_client import TTSClientPort

logger = logging.getLogger(__name__)


class GPTSoVITSHTTPClient(TTSClientPort):
    def __init__(
        self,
        base_url: str,
        connect_timeout_sec: float,
        read_timeout_sec: float,
        retry_count: int,
        retry_base_delay_sec: float,
        retry_max_delay_sec: float,
        retry_jitter_enabled: bool,
        retry_jitter_ratio: float,
        retry_total_timeout_sec: float,
        synthesis_idempotent: bool,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._synthesis_idempotent = synthesis_idempotent
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

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speaker: Optional[str] = None,
        language: Optional[str] = None,
        reference_audio_url: Optional[str] = None,
    ) -> str:
        provider = "tts"
        operation = "synthesize"
        idempotent = self._synthesis_idempotent
        payload = self._build_request_payload(
            text=text,
            voice_id=voice_id,
            speaker=speaker,
            language=language,
            reference_audio_url=reference_audio_url,
        )

        def _retry_logger(attempt: int, exc: Exception, delay: float) -> None:
            signal = getattr(exc, "_retry_signal", None)
            log_event(
                logger,
                logging.WARNING,
                "retry scheduled",
                provider=provider,
                path="/synthesize",
                status=getattr(signal, "error_code", None),
                result="retry",
                retry_attempt=attempt,
                retry_delay_ms=round(delay * 1000, 2),
                retry_reason=str(exc),
            )

        async def _request() -> str:
            started = time.perf_counter()
            try:
                response = await self._client.post(f"{self._base_url}/synthesize", json=payload)
            except httpx.ConnectTimeout as exc:
                duration = time.perf_counter() - started
                observe_provider_latency(provider, operation, "failure", duration)
                log_event(logger, logging.ERROR, "tts connect timeout", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status="connect_timeout")
                err = TTSTimeoutError("tts provider connect timeout")
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
                log_event(logger, logging.ERROR, "tts read timeout", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status="read_timeout")
                err = TTSTimeoutError("tts provider read timeout")
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
                log_event(logger, logging.ERROR, "tts timeout", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status="total_timeout")
                err = TTSTimeoutError("tts provider total timeout")
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
                log_event(logger, logging.ERROR, "tts transient network error", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status="network_error")
                err = TTSBadResponseError("tts transient network error")
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
                log_event(logger, logging.ERROR, "tts call transport error", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status="error")
                err = TTSBadResponseError("tts transport error")
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
                log_event(logger, logging.ERROR, "tts call bad status", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status=str(response.status_code))
                err = TTSBadResponseError(f"tts status={response.status_code}")
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
                log_event(logger, logging.ERROR, "tts invalid json", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="failure", status="invalid_json")
                err = TTSBadResponseError("tts response is not valid json")
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

            audio_location = self._parse_audio_location(body)
            observe_provider_latency(provider, operation, "success", duration)
            log_event(logger, logging.INFO, "tts call success", provider=provider, path="/synthesize", latency_ms=round(duration * 1000, 2), result="success", status="ok")
            return audio_location

        try:
            return await run_with_retry(
                operation=_request,
                policy=self._retry_policy,
                on_retry=_retry_logger,
            )
        except (TTSTimeoutError, TTSBadResponseError):
            raise
        except Exception as exc:
            raise TTSBadResponseError("tts synthesis failed") from exc

    def _build_request_payload(
        self,
        text: str,
        voice_id: Optional[str],
        speaker: Optional[str],
        language: Optional[str],
        reference_audio_url: Optional[str],
    ) -> dict[str, Any]:
        return {
            "text": text,
            "reference": {
                "voice_id": voice_id,
                "speaker": speaker,
                "language": language,
                "audio_url": reference_audio_url,
            },
        }

    def _parse_audio_location(self, body: dict[str, Any]) -> str:
        if isinstance(body.get("audio_url"), str) and body["audio_url"].strip():
            return body["audio_url"]
        if isinstance(body.get("file_path"), str) and body["file_path"].strip():
            return body["file_path"]
        if isinstance(body.get("audio_base64"), str) and body["audio_base64"].strip():
            return f"base64:{body['audio_base64']}"
        if isinstance(body.get("audio"), str) and body["audio"].strip():
            return f"base64:{body['audio']}"
        err = TTSBadResponseError("tts response has no audio payload")
        attach_retry_signal(
            err,
            RetrySignal(
                provider="tts",
                operation="synthesize",
                idempotent=self._synthesis_idempotent,
                error_code=err.error_code,
                exception_type="invalid_body",
            ),
        )
        raise err

    async def ping(self) -> bool:
        started = time.perf_counter()
        try:
            response = await self._client.get(f"{self._base_url}/health")
            ok = response.status_code < 500
            duration = time.perf_counter() - started
            observe_provider_latency("tts", "ping", "success" if ok else "failure", duration)
            return ok
        except Exception:
            duration = time.perf_counter() - started
            observe_provider_latency("tts", "ping", "failure", duration)
            return False

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
