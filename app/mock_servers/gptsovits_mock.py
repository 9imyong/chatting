from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="gptsovits-mock")


class SynthesizeRequest(BaseModel):
    text: str
    reference: dict | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "provider": "gptsovits-mock"}


@app.post("/synthesize")
async def synthesize(payload: SynthesizeRequest) -> dict:
    safe = payload.text[:24].replace(" ", "_")
    return {
        "audio_url": f"https://audio.mock.local/{safe}.wav",
    }

