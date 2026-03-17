import logging
import json
import asyncio
import time

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps.providers import get_chat_service
from app.api.schemas.chat import ChatData, ChatRequest, ChatResponse
from app.api.schemas.streaming import ChatStreamRequest
from app.application.services.chat_orchestration_service import ChatOrchestrationService
from app.common.logging.logger import log_event
from app.common.metrics.metrics import (
    observe_chat_request,
    observe_stream_disconnect,
    observe_stream_error,
    observe_stream_request,
    stream_connection_closed,
    stream_connection_opened,
)
from app.common.config.settings import get_settings
from app.common.tracing.context import request_id_ctx, trace_id_ctx

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: ChatOrchestrationService = Depends(get_chat_service),
) -> ChatResponse:
    started = time.perf_counter()
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

    duration = time.perf_counter() - started
    observe_chat_request(payload.response_mode, "success", duration)
    log_event(
        logger,
        logging.INFO,
        "chat request processed",
        session_id=payload.session_id,
        path="/api/v1/chat",
        latency_ms=round(duration * 1000, 2),
        result="success",
        status="ok",
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


def _format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    request: Request,
    service: ChatOrchestrationService = Depends(get_chat_service),
) -> StreamingResponse:
    settings = get_settings()
    stream_timeout_sec = settings.STREAM_TOTAL_TIMEOUT_SEC
    request_id = request_id_ctx.get()
    trace_id = trace_id_ctx.get()
    path = "/api/v1/chat/stream"

    async def event_generator():
        started = time.perf_counter()
        result = "success"
        stream_connection_opened()
        log_event(
            logger,
            logging.INFO,
            "stream request started",
            session_id=payload.session_id,
            path=path,
            result="success",
            status="ok",
            stream_status="start",
        )
        try:
            async for event in service.stream_chat(
                session_id=payload.session_id,
                user_message=payload.message,
                request_id=request_id,
                trace_id=trace_id,
            ):
                if await request.is_disconnected():
                    result = "disconnect"
                    observe_stream_disconnect("client_disconnected")
                    log_event(
                        logger,
                        logging.WARNING,
                        "stream client disconnected",
                        session_id=payload.session_id,
                        path=path,
                        result="disconnect",
                        status="cancelled",
                        stream_status="disconnected",
                        disconnect_reason="client_disconnected",
                    )
                    break

                elapsed = time.perf_counter() - started
                if elapsed > stream_timeout_sec:
                    result = "timeout"
                    observe_stream_error("INTERNAL_ERROR")
                    yield _format_sse(
                        "error",
                        {"error": {"code": "INTERNAL_ERROR", "message": "stream timeout exceeded"}},
                    )
                    break

                if event.event == "error":
                    result = "error"
                    error_code = event.data.get("error", {}).get("code", "INTERNAL_ERROR")
                    observe_stream_error(error_code)

                yield _format_sse(event.event, event.data)

                if event.event in {"done", "error"}:
                    break
        except asyncio.CancelledError:
            result = "disconnect"
            observe_stream_disconnect("client_cancelled")
            log_event(
                logger,
                logging.WARNING,
                "stream cancelled",
                session_id=payload.session_id,
                path=path,
                result="disconnect",
                status="cancelled",
                stream_status="cancelled",
                disconnect_reason="client_cancelled",
            )
        finally:
            duration = time.perf_counter() - started
            observe_stream_request(result, duration)
            stream_connection_closed()
            log_event(
                logger,
                logging.INFO,
                "stream request completed",
                session_id=payload.session_id,
                path=path,
                latency_ms=round(duration * 1000, 2),
                result=result,
                status="ok" if result == "success" else "error",
                stream_status=result,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
