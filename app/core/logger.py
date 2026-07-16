"""Logging configuration.

Logs go to stdout (for container collection) and to app/logs/app.log.
Call ``configure_logging()`` once at startup, then ``get_logger(__name__)``
everywhere else.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.core.config import settings

_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.LOG_DIR / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(stream)
    root.addHandler(file_handler)

    # quiet noisy libraries unless debugging
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(
            logging.INFO if settings.DEBUG else logging.WARNING
        )

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)