from fastapi import APIRouter, Depends

from app.api.deps.providers import get_chat_service
from app.api.schemas.chat import ChatData, ChatRequest, ChatResponse
from app.application.services.chat_orchestration_service import ChatOrchestrationService
from app.common.tracing.context import request_id_ctx, trace_id_ctx

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: ChatOrchestrationService = Depends(get_chat_service),
) -> ChatResponse:
    generate_audio = payload.response_mode == "text_audio"
    result = await service.chat(
        session_id=payload.session_id,
        user_message=payload.message,
        generate_audio=generate_audio,
        voice_id=payload.voice_id,
        speaker=payload.speaker,
        language=payload.language,
        reference_audio_url=payload.reference_audio_url,
    )
    return ChatResponse(
        request_id=request_id_ctx.get(),
        trace_id=trace_id_ctx.get(),
        data=ChatData(
            text=result.text,
            audio_url=result.audio_url,
            response_mode=payload.response_mode,
        ),
    )
