"""Structured, searchable event logging built on the standard ``logging`` module.

Every line looks like:

    2026-10-03 10:30:16,120 | INFO | FACE_REGISTERED | face_id=F001 track_id=17

* The first token after the level is the event name (grep-friendly).
* Fields are ``key=value`` pairs.
* NumPy arrays (e.g. embeddings) are never written - only a placeholder.
* The file handler flushes after every record, so lines survive a crash.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.errors import ConfigError

LOGGER_NAME = "katomaran.events"

# Event names used across the application (kept here so they stay consistent).
APPLICATION_START = "APPLICATION_START"
APPLICATION_STOP = "APPLICATION_STOP"
FACE_DETECTED = "FACE_DETECTED"
TRACK_CREATED = "TRACK_CREATED"
TRACK_LOST = "TRACK_LOST"
EMBEDDING_GENERATED = "EMBEDDING_GENERATED"
FACE_REGISTERED = "FACE_REGISTERED"
FACE_RECOGNIZED = "FACE_RECOGNIZED"
ENTRY = "ENTRY"
EXIT = "EXIT"
DATABASE_ERROR = "DATABASE_ERROR"
RTSP_ERROR = "RTSP_ERROR"
IMAGE_ERROR = "IMAGE_ERROR"
RECOGNITION_FAILED = "RECOGNITION_FAILED"
CONFIG_WARNING = "CONFIG_WARNING"


def _format_value(value: Any) -> str:
    if isinstance(value, np.ndarray):
        return "<array omitted>"  # privacy: never log embeddings
    if isinstance(value, float):
        return f"{value:.3f}"
    text = str(value)
    return f'"{text}"' if " " in text else text


class EventLogger:
    """Thin wrapper that formats ``event + key=value`` messages."""

    def __init__(self, log_file: Path, level: str = "INFO", console: bool = True) -> None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"Cannot create log file {log_file}: {exc}") from exc

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler.setFormatter(formatter)
        self._logger = logging.getLogger(f"{LOGGER_NAME}.{id(self)}")
        self._logger.setLevel(level.upper())
        self._logger.propagate = False
        self._logger.addHandler(file_handler)
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)
        self.log_file = log_file

    def log(self, event: str, level: int = logging.INFO, **fields: Any) -> None:
        parts = [event]
        if fields:
            parts.append(" ".join(f"{k}={_format_value(v)}" for k, v in fields.items()))
        self._logger.log(level, " | ".join(parts))

    def info(self, event: str, **fields: Any) -> None:
        self.log(event, logging.INFO, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self.log(event, logging.WARNING, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log(event, logging.ERROR, **fields)

    def close(self) -> None:
        for handler in list(self._logger.handlers):
            handler.flush()
            handler.close()
            self._logger.removeHandler(handler)
