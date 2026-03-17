from __future__ import annotations

from typing import Any, AsyncIterator, Optional

from pydantic import BaseModel

from app.application.services.history_builder import build_prompt_history, trim_history_for_storage
from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import DomainError, ExternalServiceError, ValidationError
from app.ports.outbound.llm_client import LLMClientPort
from app.ports.outbound.session_repository import SessionRepositoryPort
from app.ports.outbound.tts_client import TTSClientPort


class ChatResult(BaseModel):
    text: str
    audio_url: Optional[str] = None


class StreamEvent(BaseModel):
    event: str
    data: dict[str, Any]


class ChatOrchestrationService:
    def __init__(
        self,
        llm_client: LLMClientPort,
        tts_client: TTSClientPort,
        session_repo: SessionRepositoryPort,
        max_history_turns: int,
        stream_chunk_size: int,
    ) -> None:
        self._llm_client = llm_client
        self._tts_client = tts_client
        self._session_repo = session_repo
        self._max_history_turns = max_history_turns
        self._stream_chunk_size = max(1, stream_chunk_size)

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

    async def stream_chat(
        self,
        session_id: str,
        user_message: str,
        request_id: str,
        trace_id: str,
    ) -> AsyncIterator[StreamEvent]:
        yield StreamEvent(
            event="start",
            data={
                "request_id": request_id,
                "trace_id": trace_id,
                "session_id": session_id,
            },
        )

        try:
            if not user_message.strip():
                raise ValidationError("message must not be empty")

            history = await self._session_repo.get_history(session_id)
            prompt_messages = build_prompt_history(
                history=history,
                user_message=user_message,
                max_turns=self._max_history_turns,
            )

            chunks: list[str] = []
            sequence = 0
            generate_stream = getattr(self._llm_client, "generate_stream", None)

            if callable(generate_stream):
                async for chunk in generate_stream(prompt_messages):
                    if not chunk:
                        continue
                    sequence += 1
                    chunks.append(chunk)
                    yield StreamEvent(event="token", data={"delta": chunk, "sequence": sequence})
            else:
                assistant_text = await self._llm_client.generate(prompt_messages)
                for chunk in self._chunk_text(assistant_text):
                    sequence += 1
                    chunks.append(chunk)
                    yield StreamEvent(event="token", data={"delta": chunk, "sequence": sequence})

            assistant_text = "".join(chunks).strip()
            if not assistant_text:
                raise ExternalServiceError("empty response from llm")

            current_user = ChatMessage(role="user", content=user_message)
            assistant_msg = ChatMessage(role="assistant", content=assistant_text)
            compacted = trim_history_for_storage([*history, current_user, assistant_msg], self._max_history_turns)
            await self._session_repo.set_history(session_id, compacted)

            yield StreamEvent(event="done", data={"finish_reason": "stop", "usage": None})
        except DomainError as exc:
            yield StreamEvent(
                event="error",
                data={
                    "error": {
                        "code": getattr(exc, "error_code", "DOMAIN_ERROR"),
                        "message": str(exc),
                    }
                },
            )
        except Exception:
            yield StreamEvent(
                event="error",
                data={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "streaming request failed",
                    }
                },
            )

    def _chunk_text(self, text: str) -> list[str]:
        if not text:
            return []
        return [text[i : i + self._stream_chunk_size] for i in range(0, len(text), self._stream_chunk_size)]

    async def readiness_details(self) -> tuple[bool, dict[str, str]]:
        checks = {
            "session_repository": await self._session_repo.ping(),
            "llm_client": await self._llm_client.ping(),
            "tts_client": await self._tts_client.ping(),
        }
        status_map = {name: ("up" if ok else "down") for name, ok in checks.items()}
        return all(checks.values()), status_map
