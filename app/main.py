from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.bootstrap import AppContainer, build_container, close_container
from app.common.config.settings import Settings, get_settings
from app.common.logging.logger import configure_logging, log_event
from app.common.metrics.metrics import MetricsMiddleware
from app.common.tracing.context import request_id_ctx, trace_id_ctx
from app.domain.exceptions.errors import (
    DomainError,
    ExternalServiceError,
    ForbiddenError,
    RateLimitExceededError,
    UnauthorizedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    _settings = settings or get_settings()
    configure_logging(_settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container: AppContainer = await build_container(_settings)
        app.state.container = container
        app.state.bootstrap_complete = True
        app.state.readiness_last_success = {}
        try:
            yield
        finally:
            app.state.bootstrap_complete = False
            await close_container(container)

    app = FastAPI(title=_settings.APP_NAME, lifespan=lifespan)
    app.add_middleware(MetricsMiddleware)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        started = time.perf_counter()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request_id_ctx.set(request_id)
        trace_id_ctx.set(trace_id)

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-trace-id"] = trace_id

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            logger,
            logging.INFO,
            "http request handled",
            path=request.url.path,
            latency_ms=latency_ms,
            status=str(response.status_code),
            result="success" if response.status_code < 500 else "failure",
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": "invalid request payload",
                    "request_id": request_id_ctx.get(),
                    "trace_id": trace_id_ctx.get(),
                }
            },
        )

    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError):
        log_event(
            logger,
            logging.ERROR,
            "domain exception",
            path=request.url.path,
            status="error",
            result="failure",
        )
        status_code = 400
        if isinstance(exc, (ExternalServiceError,)):
            status_code = 503
        elif isinstance(exc, ValidationError):
            status_code = 422
        elif isinstance(exc, UnauthorizedError):
            status_code = 401
        elif isinstance(exc, ForbiddenError):
            status_code = 403
        elif isinstance(exc, RateLimitExceededError):
            status_code = 429
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": getattr(exc, "error_code", "DOMAIN_ERROR"),
                    "message": str(exc),
                    "request_id": request_id_ctx.get(),
                    "trace_id": trace_id_ctx.get(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log_event(
            logger,
            logging.ERROR,
            "unhandled exception",
            path=request.url.path,
            status="error",
            result="failure",
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "internal server error",
                    "request_id": request_id_ctx.get(),
                    "trace_id": trace_id_ctx.get(),
                }
            },
        )

    app.include_router(health_router)
    app.include_router(chat_router)

    return app


app = create_app()
