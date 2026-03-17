import time

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_TOTAL = Counter("app_request_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "HTTP request latency", ["method", "path"])
IN_PROGRESS = Gauge("app_request_in_progress", "In-progress requests")

CHAT_REQUEST_TOTAL = Counter("chat_request_total", "Chat request count", ["response_mode", "result"])
CHAT_REQUEST_LATENCY = Histogram("chat_request_latency_seconds", "Chat request latency", ["response_mode", "result"])

PROVIDER_LATENCY = Histogram(
    "provider_latency_seconds",
    "Provider call latency",
    ["provider", "operation", "result"],
)

READINESS_PROBE_LATENCY = Histogram(
    "readiness_probe_latency_seconds",
    "Readiness probe latency",
    ["dependency", "result"],
)

STREAM_ACTIVE_CONNECTIONS = Gauge("chat_stream_active_connections", "Active streaming connections")
STREAM_REQUEST_TOTAL = Counter("chat_stream_request_total", "Streaming request count", ["result"])
STREAM_DURATION = Histogram("chat_stream_duration_seconds", "Streaming request duration", ["result"])
STREAM_DISCONNECT_TOTAL = Counter("chat_stream_disconnect_total", "Streaming disconnect count", ["reason"])
STREAM_ERROR_TOTAL = Counter("chat_stream_error_total", "Streaming error count", ["error_code"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        method = request.method
        path = request.url.path
        start = time.perf_counter()
        IN_PROGRESS.inc()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            REQUEST_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            IN_PROGRESS.dec()


def observe_chat_request(response_mode: str, result: str, duration_sec: float) -> None:
    CHAT_REQUEST_TOTAL.labels(response_mode=response_mode, result=result).inc()
    CHAT_REQUEST_LATENCY.labels(response_mode=response_mode, result=result).observe(duration_sec)


def observe_provider_latency(provider: str, operation: str, result: str, duration_sec: float) -> None:
    PROVIDER_LATENCY.labels(provider=provider, operation=operation, result=result).observe(duration_sec)


def observe_readiness_probe(dependency: str, result: str, duration_sec: float) -> None:
    READINESS_PROBE_LATENCY.labels(dependency=dependency, result=result).observe(duration_sec)


def stream_connection_opened() -> None:
    STREAM_ACTIVE_CONNECTIONS.inc()


def stream_connection_closed() -> None:
    STREAM_ACTIVE_CONNECTIONS.dec()


def observe_stream_request(result: str, duration_sec: float) -> None:
    STREAM_REQUEST_TOTAL.labels(result=result).inc()
    STREAM_DURATION.labels(result=result).observe(duration_sec)


def observe_stream_disconnect(reason: str) -> None:
    STREAM_DISCONNECT_TOTAL.labels(reason=reason).inc()


def observe_stream_error(error_code: str) -> None:
    STREAM_ERROR_TOTAL.labels(error_code=error_code).inc()


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
