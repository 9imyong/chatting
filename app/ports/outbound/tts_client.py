from typing import Optional, Protocol


class TTSClientPort(Protocol):
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speaker: Optional[str] = None,
        language: Optional[str] = None,
        reference_audio_url: Optional[str] = None,
    ) -> str:
        ...

    async def ping(self) -> bool:
        ...

    async def close(self) -> None:
        ...
