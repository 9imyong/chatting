import json
import logging

from app.common.logging.logger import JsonFormatter, log_event


def test_json_formatter_includes_standard_fields() -> None:
    logger = logging.getLogger("test.logger")
    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    log_event(
        logger,
        logging.INFO,
        "structured test",
        session_id="s1",
        provider="llm",
        path="/api/v1/chat",
        latency_ms=10.2,
        result="success",
        status="ok",
        user_text="should_be_removed",
    )

    formatter = JsonFormatter()
    rendered = formatter.format(records[0])
    payload = json.loads(rendered)

    assert payload["session_id"] == "s1"
    assert payload["provider"] == "llm"
    assert payload["path"] == "/api/v1/chat"
    assert payload["latency_ms"] == 10.2
    assert payload["result"] == "success"
    assert payload["status"] == "ok"

    logger.handlers = []
