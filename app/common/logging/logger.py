import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.common.tracing.context import request_id_ctx, trace_id_ctx

SENSITIVE_KEYS = {
    "user_text",
    "message",
    "prompt",
    "token",
    "audio",
    "audio_base64",
    "authorization",
    "auth_header",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extra_fields = getattr(record, "event_fields", {}) or {}
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "trace_id": trace_id_ctx.get(),
            "tenant_id": extra_fields.get("tenant_id"),
            "session_id": extra_fields.get("session_id"),
            "provider": extra_fields.get("provider"),
            "path": extra_fields.get("path"),
            "latency_ms": extra_fields.get("latency_ms"),
            "result": extra_fields.get("result"),
            "status": extra_fields.get("status"),
            "retry_attempt": extra_fields.get("retry_attempt"),
            "retry_delay_ms": extra_fields.get("retry_delay_ms"),
            "retry_reason": extra_fields.get("retry_reason"),
            "stream_status": extra_fields.get("stream_status"),
            "disconnect_reason": extra_fields.get("disconnect_reason"),
        }
        return json.dumps(payload, ensure_ascii=False)


def sanitize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in fields.items():
        if key in SENSITIVE_KEYS:
            continue
        sanitized[key] = value
    return sanitized


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    logger.log(level, message, extra={"event_fields": sanitize_fields(fields)})


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
