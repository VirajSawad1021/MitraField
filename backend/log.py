"""Structured logging. One JSON object per line on stdout, which Cloud Logging parses natively
(`severity`, `message`, and the extra fields become queryable)."""
import json
import logging
import sys
import time

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, r):
        row = {"severity": r.levelname, "message": r.getMessage(), "logger": r.name,
               "time": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(r.created)) + f".{int(r.msecs):03d}Z"}
        row.update({k: v for k, v in r.__dict__.items() if k not in _RESERVED})
        if r.exc_info:
            row["stack_trace"] = self.formatException(r.exc_info)
        return json.dumps(row, default=str)


def setup(level="INFO"):
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(level)
    logging.getLogger("uvicorn.access").setLevel("WARNING")   # one line per request is noise; app logs say more


def get(name):
    return logging.getLogger(f"mitrafield.{name}")
