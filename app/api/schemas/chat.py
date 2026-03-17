from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1)
    response_mode: str = Field(default="text", pattern="^(text|text_audio)$")
    voice_id: Optional[str] = None
    speaker: Optional[str] = None
    language: Optional[str] = None
    reference_audio_url: Optional[str] = None


class ChatData(BaseModel):
    text: str
    audio_url: Optional[str] = None
    response_mode: str


class ChatResponse(BaseModel):
    status: str = "success"
    message: str = "chat completed"
    request_id: str
    trace_id: str
    data: ChatData
