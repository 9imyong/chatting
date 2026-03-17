from datetime import datetime, timezone
import logging
import time

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.api.deps.providers import get_container
from app.common.logging.logger import log_event
from app.common.metrics.metrics import metrics_response, observe_readiness_probe

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


async def _probe_dependency(request: Request, key: str, probe_coro):
    started = time.perf_counter()
    ok = False
    reason = None
    try:
        ok = bool(await probe_coro())
        if not ok:
            reason = "health probe returned false"
    except Exception:
        ok = False
        reason = "health probe raised exception"
    duration_sec = time.perf_counter() - started
    latency_ms = round(duration_sec * 1000, 2)

    observe_readiness_probe(key, "success" if ok else "failure", duration_sec)

    cache: dict[str, str] = request.app.state.readiness_last_success
    if ok:
        cache[key] = datetime.now(timezone.utc).isoformat()

    log_event(
        logger,
        logging.INFO,
        "readiness probe executed",
        path="/ready",
        provider=key,
        latency_ms=latency_ms,
        result="success" if ok else "failure",
        status="ok" if ok else "fail",
    )

    result = {
        "status": "ok" if ok else "fail",
        "latency_ms": latency_ms,
        "reason": reason,
    }
    if key in {"llm", "tts"}:
        result["last_success_ts"] = cache.get(key)
    return ok, result


@router.get("/ready")
async def ready(request: Request):
    bootstrap_complete = bool(getattr(request.app.state, "bootstrap_complete", False))
    if not bootstrap_complete:
        content = {
            "status": "fail",
            "dependencies": {
                "llm": {"status": "fail", "latency_ms": None, "last_success_ts": None, "reason": "bootstrap incomplete"},
                "tts": {"status": "fail", "latency_ms": None, "last_success_ts": None, "reason": "bootstrap incomplete"},
                "session_store": {"status": "fail", "latency_ms": None, "reason": "bootstrap incomplete"},
            },
        }
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=content)

    container = get_container(request)
    llm_ok, llm_probe = await _probe_dependency(request, "llm", container.llm_client.ping)
    tts_ok, tts_probe = await _probe_dependency(request, "tts", container.tts_client.ping)
    session_ok, session_probe = await _probe_dependency(
        request,
        "session_store",
        container.session_repo.ping,
    )
    rate_limit_enabled = bool(getattr(container.settings, "RATE_LIMIT_ENABLED", False))
    rate_limit_probe = None
    rate_limit_ok = True
    if rate_limit_enabled:
        rate_limit_ok, rate_limit_probe = await _probe_dependency(
            request,
            "rate_limiter",
            container.rate_limiter.ping,
        )

    oks = [llm_ok, tts_ok, session_ok]
    if rate_limit_enabled:
        oks.append(rate_limit_ok)
    if all(oks):
        overall = "ok"
        http_code = status.HTTP_200_OK
    elif any(oks):
        overall = "degraded"
        http_code = status.HTTP_200_OK
    else:
        overall = "fail"
        http_code = status.HTTP_503_SERVICE_UNAVAILABLE

    content = {
        "status": overall,
        "dependencies": {
            "llm": llm_probe,
            "tts": tts_probe,
            "session_store": session_probe,
        },
    }
    if rate_limit_enabled and rate_limit_probe is not None:
        content["dependencies"]["rate_limiter"] = rate_limit_probe
    if http_code == status.HTTP_200_OK:
        return content
    return JSONResponse(status_code=http_code, content=content)


@router.get("/metrics")
async def metrics():
    return metrics_response()
