import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log event without serializing application secrets."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app_env: str) -> None:
    """Configure structured logging without rendering settings or request bodies."""
    level = logging.DEBUG if app_env == "development" else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
