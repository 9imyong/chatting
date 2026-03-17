from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="vllm-mock")


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float | None = None
    max_tokens: int | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "provider": "vllm-mock"}


@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest) -> dict:
    last_user = ""
    for msg in reversed(payload.messages):
        if msg.get("role") == "user":
            last_user = str(msg.get("content", ""))
            break

    text = f"mock-vllm-reply: {last_user}".strip()
    return {
        "id": "cmpl-mock-1",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }

