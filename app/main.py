from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.bootstrap import AppContainer, build_container, close_container
from app.common.config.settings import Settings, get_settings
from app.common.logging.logger import configure_logging
from app.common.metrics.metrics import MetricsMiddleware
from app.common.tracing.context import request_id_ctx, trace_id_ctx
from app.domain.exceptions.errors import DomainError, ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    _settings = settings or get_settings()
    configure_logging(_settings.LOG_LEVEL)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container: AppContainer = await build_container(_settings)
        app.state.container = container
        app.state.bootstrap_complete = True
        try:
            yield
        finally:
            app.state.bootstrap_complete = False
            await close_container(container)

    app = FastAPI(title=_settings.APP_NAME, lifespan=lifespan)
    app.add_middleware(MetricsMiddleware)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request_id_ctx.set(request_id)
        trace_id_ctx.set(trace_id)

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-trace-id"] = trace_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "internal server error",
                "request_id": request_id_ctx.get(),
                "trace_id": trace_id_ctx.get(),
                "error_code": "INTERNAL_ERROR",
            },
        )

    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError):
        logger.warning("domain exception: %s", str(exc))
        status_code = 400
        if isinstance(exc, ExternalServiceError):
            status_code = 503
        elif isinstance(exc, ValidationError):
            status_code = 422
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "message": str(exc),
                "request_id": request_id_ctx.get(),
                "trace_id": trace_id_ctx.get(),
                "error_code": getattr(exc, "error_code", "DOMAIN_ERROR"),
            },
        )

    app.include_router(health_router)
    app.include_router(chat_router)

    return app


app = create_app()
