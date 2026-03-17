from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.application.services.history_builder import build_prompt_history, trim_history_for_storage
from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import ExternalServiceError, ValidationError
from app.ports.outbound.llm_client import LLMClientPort
from app.ports.outbound.session_repository import SessionRepositoryPort
from app.ports.outbound.tts_client import TTSClientPort


class ChatResult(BaseModel):
    text: str
    audio_url: Optional[str] = None


class ChatOrchestrationService:
    def __init__(
        self,
        llm_client: LLMClientPort,
        tts_client: TTSClientPort,
        session_repo: SessionRepositoryPort,
        max_history_turns: int,
    ) -> None:
        self._llm_client = llm_client
        self._tts_client = tts_client
        self._session_repo = session_repo
        self._max_history_turns = max_history_turns

    async def chat(
        self,
        session_id: str,
        user_message: str,
        generate_audio: bool,
        voice_id: Optional[str],
        speaker: Optional[str] = None,
        language: Optional[str] = None,
        reference_audio_url: Optional[str] = None,
    ) -> ChatResult:
        if not user_message.strip():
            raise ValidationError("message must not be empty")

        history = await self._session_repo.get_history(session_id)
        prompt_messages = build_prompt_history(
            history=history,
            user_message=user_message,
            max_turns=self._max_history_turns,
        )

        assistant_text = await self._llm_client.generate(prompt_messages)
        if not assistant_text:
            raise ExternalServiceError("empty response from llm")

        current_user = ChatMessage(role="user", content=user_message)
        assistant_msg = ChatMessage(role="assistant", content=assistant_text)
        compacted = trim_history_for_storage([*history, current_user, assistant_msg], self._max_history_turns)
        await self._session_repo.set_history(session_id, compacted)

        if not generate_audio:
            return ChatResult(text=assistant_text)

        audio_url = await self._tts_client.synthesize(
            text=assistant_text,
            voice_id=voice_id,
            speaker=speaker,
            language=language,
            reference_audio_url=reference_audio_url,
        )
        return ChatResult(text=assistant_text, audio_url=audio_url)

    async def readiness_details(self) -> tuple[bool, dict[str, str]]:
        checks = {
            "session_repository": await self._session_repo.ping(),
            "llm_client": await self._llm_client.ping(),
            "tts_client": await self._tts_client.ping(),
        }
        status_map = {name: ("up" if ok else "down") for name, ok in checks.items()}
        return all(checks.values()), status_map
