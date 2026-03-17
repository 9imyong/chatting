from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1)
    # Phase-1 streaming is text only.
    response_mode: str = Field(default="text", pattern="^text$")


class StreamStartData(BaseModel):
    request_id: str
    trace_id: str
    session_id: str


class StreamTokenData(BaseModel):
    delta: str
    sequence: int


class StreamDoneData(BaseModel):
    finish_reason: str = "stop"
    usage: Optional[dict[str, Any]] = None


class StreamErrorDetail(BaseModel):
    code: str
    message: str


class StreamErrorData(BaseModel):
    error: StreamErrorDetail

