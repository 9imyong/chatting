from typing import Optional

from app.ports.outbound.tts_client import TTSClientPort


class GPTSoVITSStubClient(TTSClientPort):
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        speaker: Optional[str] = None,
        language: Optional[str] = None,
        reference_audio_url: Optional[str] = None,
    ) -> str:
        safe = text[:32].replace(" ", "_")
        voice = voice_id or speaker or "default"
        return f"https://audio.local/{voice}/{safe}.wav"

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None
