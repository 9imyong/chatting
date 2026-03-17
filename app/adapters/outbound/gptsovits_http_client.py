from typing import Optional

import httpx

from app.common.utils.retry import run_with_retry
from app.domain.exceptions.errors import ExternalServiceError
from app.ports.outbound.tts_client import TTSClientPort


class GPTSoVITSHTTPClient(TTSClientPort):
    def __init__(
        self,
        base_url: str,
        connect_timeout_sec: float,
        read_timeout_sec: float,
        retry_count: int,
        retry_base_delay_sec: float,
        retry_max_delay_sec: float,
        retry_jitter_sec: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._retry_count = retry_count
        self._retry_base_delay_sec = retry_base_delay_sec
        self._retry_max_delay_sec = retry_max_delay_sec
        self._retry_jitter_sec = retry_jitter_sec
        timeout = httpx.Timeout(connect=connect_timeout_sec, read=read_timeout_sec, write=read_timeout_sec, pool=connect_timeout_sec)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speaker: Optional[str] = None,
        language: Optional[str] = None,
        reference_audio_url: Optional[str] = None,
    ) -> str:
        payload = {
            "text": text,
            "voice_id": voice_id,
            "speaker": speaker,
            "language": language,
            "reference_audio_url": reference_audio_url,
        }

        async def _request() -> str:
            response = await self._client.post(f"{self._base_url}/synthesize", json=payload)
            response.raise_for_status()
            body = response.json()
            audio_url = body.get("audio_url") or body.get("file_path")
            if not audio_url:
                raise ExternalServiceError("GPT-SoVITS response has no audio location")
            return audio_url

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
            raise ExternalServiceError("GPT-SoVITS synthesis failed") from exc

    async def ping(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/health")
            return response.status_code < 500
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
