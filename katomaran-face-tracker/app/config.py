"""Configuration loading and validation.

All tunable values live in config.json. This module turns the JSON into typed
dataclasses and rejects bad values early with a clear ConfigError, so the rest
of the application can trust its inputs.

Secrets (e.g. RTSP URLs with passwords) are NOT stored in config.json. Use
``"source": "env:RTSP_URL"`` and put the real URL in the environment or in a
git-ignored ``.env`` file.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Type, TypeVar
from urllib.parse import urlsplit, urlunsplit

from app.errors import ConfigError

T = TypeVar("T")

SOURCE_TYPES = ("video", "rtsp")
COUNTING_SCOPES = ("all_time", "session")


@dataclass
class InputConfig:
    source: str = "sample_video.mp4"
    source_type: str = "video"
    reconnect_max_attempts: int = 10
    reconnect_delay_seconds: float = 2.0
    read_timeout_seconds: float = 10.0


@dataclass
class DetectionConfig:
    model: str = "models/yolov8n-face.pt"
    confidence_threshold: float = 0.5
    skip_frames: int = 4
    device: str = "auto"  # auto | cpu | cuda | 0 | 1 ...
    image_size: int = 640


@dataclass
class TrackingConfig:
    max_missing_seconds: float = 2.0
    low_confidence_threshold: float = 0.2
    match_iou_threshold: float = 0.3
    low_match_iou_threshold: float = 0.5
    track_buffer_seconds: float = 2.0


@dataclass
class RecognitionConfig:
    model_pack: str = "buffalo_l"
    similarity_threshold: float = 0.45
    embeddings_per_decision: int = 3
    max_resolve_attempts: int = 12


@dataclass
class QualityConfig:
    min_face_size_px: int = 48
    blur_threshold: float = 30.0
    min_detection_confidence: float = 0.6
    reject_edge_touching: bool = True
    edge_margin_px: int = 2


@dataclass
class DatabaseConfig:
    path: str = "data/faces.db"


@dataclass
class LoggingConfig:
    file: str = "logs/events.log"
    level: str = "INFO"
    console: bool = True


@dataclass
class StorageConfig:
    root: str = "logs"
    jpeg_quality: int = 90
    crop_padding_ratio: float = 0.25


@dataclass
class DisplayConfig:
    enabled: bool = True
    window_name: str = "Katomaran Face Tracker"


@dataclass
class CountingConfig:
    scope: str = "all_time"


@dataclass
class AppConfig:
    input: InputConfig = field(default_factory=InputConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    recognition: RecognitionConfig = field(default_factory=RecognitionConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    counting: CountingConfig = field(default_factory=CountingConfig)
    base_dir: Path = field(default_factory=Path.cwd)

    def resolve(self, relative: str) -> Path:
        """Resolve a config path relative to the config file's folder."""
        path = Path(relative)
        return path if path.is_absolute() else (self.base_dir / path)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def _build(cls: Type[T], data: Dict[str, Any], section: str) -> T:
    """Create a dataclass from a dict, rejecting unknown keys and bad types."""
    if not isinstance(data, dict):
        raise ConfigError(f"Section '{section}' must be a JSON object.")
    known = {f.name: f for f in fields(cls)}  # type: ignore[arg-type]
    unknown = set(data) - set(known)
    if unknown:
        raise ConfigError(
            f"Unknown key(s) in '{section}': {sorted(unknown)}. "
            f"Allowed keys: {sorted(known)}"
        )
    default = cls()  # type: ignore[call-arg]
    for name, value in data.items():
        expected = type(getattr(default, name))
        if expected is float and isinstance(value, int) and not isinstance(value, bool):
            data[name] = float(value)
        elif expected is not type(value):
            raise ConfigError(
                f"'{section}.{name}' must be {expected.__name__}, "
                f"got {type(value).__name__} ({value!r})."
            )
    return cls(**data)  # type: ignore[call-arg]


def load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ (no overwrite)."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(path: Path | str) -> AppConfig:
    """Read, build and validate the configuration file."""
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {config_path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Top level of config.json must be a JSON object.")

    load_dotenv(config_path.parent / ".env")

    sections = {
        "input": InputConfig, "detection": DetectionConfig,
        "recognition": RecognitionConfig, "quality": QualityConfig,
        "tracking": TrackingConfig, "database": DatabaseConfig,
        "logging": LoggingConfig, "storage": StorageConfig,
        "display": DisplayConfig, "counting": CountingConfig,
    }
    unknown = set(raw) - set(sections)
    if unknown:
        raise ConfigError(f"Unknown top-level section(s): {sorted(unknown)}")
    built = {name: _build(cls, dict(raw.get(name, {})), name)
             for name, cls in sections.items()}
    cfg = AppConfig(base_dir=config_path.resolve().parent, **built)
    validate(cfg)
    return cfg


def resolve_source(cfg: AppConfig) -> str:
    """Return the real source string (expands 'env:NAME'; file paths resolved)."""
    source = cfg.input.source
    if source.startswith("env:"):
        name = source[4:]
        value = os.environ.get(name)
        if not value:
            raise ConfigError(
                f"input.source refers to environment variable '{name}' "
                "but it is not set (put it in .env or export it)."
            )
        return value
    if cfg.input.source_type == "video":
        return str(cfg.resolve(source))
    return source


def redact_url(url: str) -> str:
    """Remove user:password from a URL so it is safe to log."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<unparseable-url>"
    if parts.username or parts.password:
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        return urlunsplit((parts.scheme, f"***@{host}", parts.path, "", ""))
    return url


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigError(message)


def validate(cfg: AppConfig) -> None:
    """Raise ConfigError for any out-of-range value."""
    i, d, r, q, t = cfg.input, cfg.detection, cfg.recognition, cfg.quality, cfg.tracking
    _require(i.source_type in SOURCE_TYPES, f"input.source_type must be one of {SOURCE_TYPES}.")
    _require(bool(i.source.strip()), "input.source must not be empty.")
    _require(i.reconnect_max_attempts >= 0, "input.reconnect_max_attempts must be >= 0.")
    _require(i.reconnect_delay_seconds >= 0, "input.reconnect_delay_seconds must be >= 0.")
    _require(i.read_timeout_seconds > 0, "input.read_timeout_seconds must be > 0.")
    _require(0.0 < d.confidence_threshold <= 1.0, "detection.confidence_threshold must be in (0, 1].")
    _require(d.skip_frames >= 0, "detection.skip_frames must be >= 0 (0 = detect every frame).")
    _require(d.image_size >= 32, "detection.image_size must be >= 32.")
    _require(-1.0 <= r.similarity_threshold <= 1.0, "recognition.similarity_threshold must be in [-1, 1].")
    _require(r.embeddings_per_decision >= 1, "recognition.embeddings_per_decision must be >= 1.")
    _require(r.max_resolve_attempts >= r.embeddings_per_decision,
             "recognition.max_resolve_attempts must be >= embeddings_per_decision.")
    _require(q.min_face_size_px >= 0 and q.blur_threshold >= 0, "quality thresholds must be >= 0.")
    _require(0.0 <= q.min_detection_confidence <= 1.0, "quality.min_detection_confidence must be in [0, 1].")
    _require(t.max_missing_seconds > 0, "tracking.max_missing_seconds must be > 0.")
    _require(0.0 <= t.low_confidence_threshold <= d.confidence_threshold,
             "tracking.low_confidence_threshold must be between 0 and detection.confidence_threshold.")
    _require(0.0 < t.match_iou_threshold <= 1.0 and 0.0 < t.low_match_iou_threshold <= 1.0,
             "tracking IoU thresholds must be in (0, 1].")
    _require(t.track_buffer_seconds > 0, "tracking.track_buffer_seconds must be > 0.")
    _require(bool(cfg.database.path.strip()), "database.path must not be empty.")
    _require(bool(cfg.logging.file.strip()), "logging.file must not be empty.")
    _require(cfg.logging.level.upper() in ("DEBUG", "INFO", "WARNING", "ERROR"),
             "logging.level must be DEBUG, INFO, WARNING or ERROR.")
    _require(bool(cfg.storage.root.strip()), "storage.root must not be empty.")
    _require(1 <= cfg.storage.jpeg_quality <= 100, "storage.jpeg_quality must be in [1, 100].")
    _require(0.0 <= cfg.storage.crop_padding_ratio <= 1.0, "storage.crop_padding_ratio must be in [0, 1].")
    _require(cfg.counting.scope in COUNTING_SCOPES, f"counting.scope must be one of {COUNTING_SCOPES}.")
