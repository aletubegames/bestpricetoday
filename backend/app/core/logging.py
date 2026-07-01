import logging
import sys
import json
import re
from datetime import datetime, timezone


REDACT_PATTERNS = [
    (re.compile(r'(access_token["\s:=]+)[^\s",}&]+'), r'\1[REDACTED]'),
    (re.compile(r'(refresh_token["\s:=]+)[^\s",}&]+'), r'\1[REDACTED]'),
    (re.compile(r'(APP-\d{10,}-[a-f0-9-]+)'), '[ML_TOKEN_REDACTED]'),
    (re.compile(r'(Bearer\s+)[^\s"]+'), r'\1[REDACTED]'),
    (re.compile(r'(Authorization["\s:=]+Bearer\s+)[^\s"]+'), r'\1[REDACTED]'),
]


class SanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.msg and isinstance(record.msg, str):
            for pattern, replacement in REDACT_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
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
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(SanitizingFilter())
    root.handlers.clear()
    root.addHandler(handler)


logger = logging.getLogger("bestpricetoday")
logger.addFilter(SanitizingFilter())
