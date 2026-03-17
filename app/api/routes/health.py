from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.api.deps.providers import get_container
from app.common.metrics.metrics import metrics_response
from app.common.tracing.context import request_id_ctx, trace_id_ctx

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
    bootstrap_complete = bool(getattr(request.app.state, "bootstrap_complete", False))
    if not bootstrap_complete:
        content = {
            "success": False,
            "request_id": request_id_ctx.get(),
            "trace_id": trace_id_ctx.get(),
            "data": {
                "status": "not_ready",
                "dependencies": {
                    "bootstrap": "down",
                    "session_repository": "down",
                    "llm_client": "down",
                    "tts_client": "down",
                },
            },
        }
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=content)

    container = get_container(request)
    is_ready, dep_status = await container.chat_service.readiness_details()
    dependencies = {"bootstrap": "up", **dep_status}

    content = {
        "success": is_ready,
        "request_id": request_id_ctx.get(),
        "trace_id": trace_id_ctx.get(),
        "data": {
            "status": "ready" if is_ready else "not_ready",
            "dependencies": dependencies,
        },
    }
    if is_ready:
        return content
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=content)


@router.get("/metrics")
async def metrics():
    return metrics_response()
