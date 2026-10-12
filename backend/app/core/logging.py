import logging
import sys
import json
import re
from datetime import datetime, timezone


REDACT_PATTERNS = [
    (re.compile(r'(https?://api\.telegram\.org/bot)[^/\s"]+'), r'\1[REDACTED]'),
    (re.compile(r'(access_token["\s:=]+)[^\s",}&]+'), r'\1[REDACTED]'),
    (re.compile(r'(refresh_token["\s:=]+)[^\s",}&]+'), r'\1[REDACTED]'),
    (re.compile(r'(client_secret["\s:=]+)[^\s",}&]+'), r'\1[REDACTED]'),
    (re.compile(r'(APP-\d{10,}-[a-f0-9-]+)'), '[ML_TOKEN_REDACTED]'),
    (re.compile(r'(Bearer\s+)[^\s"]+'), r'\1[REDACTED]'),
    (re.compile(r'(Authorization["\s:=]+Bearer\s+)[^\s"]+'), r'\1[REDACTED]'),
]


def _sanitize(text: str) -> str:
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            rendered = record.getMessage()
        except Exception:
            return True
        if isinstance(rendered, str):
            record.msg = _sanitize(rendered)
            record.args = ()
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(SanitizingFilter())
    root.handlers.clear()
    root.addHandler(handler)


logger = logging.getLogger("bestpricetoday")
logger.addFilter(SanitizingFilter())
