from typing import Optional

import httpx

from app.common.utils.retry import run_with_retry
from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import ExternalServiceError
from app.ports.outbound.llm_client import LLMClientPort


class VLLMHTTPClient(LLMClientPort):
    def __init__(
        self,
        base_url: str,
        model: str,
        connect_timeout_sec: float,
        read_timeout_sec: float,
        retry_count: int,
        retry_base_delay_sec: float,
        retry_max_delay_sec: float,
        retry_jitter_sec: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._retry_count = retry_count
        self._retry_base_delay_sec = retry_base_delay_sec
        self._retry_max_delay_sec = retry_max_delay_sec
        self._retry_jitter_sec = retry_jitter_sec
        timeout = httpx.Timeout(connect=connect_timeout_sec, read=read_timeout_sec, write=read_timeout_sec, pool=connect_timeout_sec)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(self, messages: list[ChatMessage]) -> str:
        payload = {
            "model": self._model,
            "messages": [m.model_dump() for m in messages],
        }

        async def _request() -> str:
            response = await self._client.post(f"{self._base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()
            choices = body.get("choices", [])
            if not choices:
                raise ExternalServiceError("vLLM response has no choices")
            content: Optional[str] = choices[0].get("message", {}).get("content")
            if not content:
                raise ExternalServiceError("vLLM response content is empty")
            return content

        try:
            return await run_with_retry(
                operation=_request,
                retry_count=self._retry_count,
                base_delay_sec=self._retry_base_delay_sec,
                max_delay_sec=self._retry_max_delay_sec,
                jitter_sec=self._retry_jitter_sec,
                retry_exceptions=(httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError),
            )
        except Exception as exc:
            raise ExternalServiceError("vLLM generation failed") from exc

    async def ping(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/health")
            return response.status_code < 500
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
