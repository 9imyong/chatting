import time
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest
from fastapi import Response

REQUEST_TOTAL = Counter("app_request_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "HTTP request latency", ["method", "path"])
IN_PROGRESS = Gauge("app_request_in_progress", "In-progress requests")


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


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
