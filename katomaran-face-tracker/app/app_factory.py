"""Composition root: builds every real component from the configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import AppConfig, redact_url, resolve_source
from app.database.sqlite_repository import SQLiteRepository
from app.detection.yolo_detector import YoloFaceDetector
from app.display import Display
from app.event_logging.event_logger import EventLogger
from app.input.video_source import FileVideoSource, RTSPVideoSource, VideoSource
from app.pipeline import Pipeline
from app.presence.event_recorder import EventRecorder
from app.presence.presence_manager import PresenceManager
from app.presence.visitor_counter import VisitorCounter
from app.recognition.face_recognizer import InsightFaceEmbedder
from app.recognition.identity_resolver import IdentityResolver
from app.recognition.quality import QualityChecker
from app.registration.face_registry import FaceRegistry
from app.storage.image_store import ImageStore
from app.tracking.tracker import ByteTracker


@dataclass
class App:
    pipeline: Pipeline
    repository: SQLiteRepository
    logger: EventLogger

    def close(self) -> None:
        self.repository.close()
        self.logger.close()


def build_source(cfg: AppConfig, logger: EventLogger) -> VideoSource:
    source = resolve_source(cfg)
    if cfg.input.source_type == "rtsp":
        return RTSPVideoSource(source, logger, cfg.input.reconnect_max_attempts,
                               cfg.input.reconnect_delay_seconds, cfg.input.read_timeout_seconds)
    return FileVideoSource(Path(source))


def build_tracker(cfg: AppConfig) -> ByteTracker:
    t = cfg.tracking
    return ByteTracker(high_threshold=cfg.detection.confidence_threshold,
                       low_threshold=t.low_confidence_threshold,
                       match_iou=t.match_iou_threshold, low_match_iou=t.low_match_iou_threshold,
                       buffer_seconds=t.track_buffer_seconds)


def build_app(cfg: AppConfig, show_display: Optional[bool] = None) -> App:
    """Create the real application (loads the YOLO and InsightFace models)."""
    logger = EventLogger(cfg.resolve(cfg.logging.file), cfg.logging.level, cfg.logging.console)
    repository = None
    try:
        source = build_source(cfg, logger)
        detector = YoloFaceDetector(cfg.resolve(cfg.detection.model),
                                    min(cfg.tracking.low_confidence_threshold, cfg.detection.confidence_threshold),
                                    cfg.detection.device, cfg.detection.image_size)
        embedder = InsightFaceEmbedder(cfg.recognition.model_pack)
        repository = SQLiteRepository(cfg.resolve(cfg.database.path))
        repository.ensure_embedding_compatibility(embedder.embedding_dim, embedder.model_name)

        images = ImageStore(cfg.resolve(cfg.storage.root), cfg.storage.jpeg_quality)
        registry = FaceRegistry.load(repository, images, logger, cfg.recognition.similarity_threshold)
        resolver = IdentityResolver(embedder, registry, QualityChecker(cfg.quality), cfg.recognition,
                                    cfg.storage.crop_padding_ratio, logger)
        pipeline = Pipeline(
            cfg, source, detector, build_tracker(cfg), resolver,
            PresenceManager(cfg.tracking.max_missing_seconds),
            EventRecorder(repository, images, logger),
            VisitorCounter(cfg.counting.scope, lambda: registry.registered_count),
            logger,
            display=Display(cfg.display.window_name) if (cfg.display.enabled if show_display is None else show_display) else None)
        logger.info("MODELS_READY", detector_device=detector.device, embedder_device=embedder.device,
                    embedding_dim=embedder.embedding_dim, known_faces=registry.registered_count,
                    source=redact_url(cfg.input.source) if cfg.input.source_type == "rtsp" else cfg.input.source)
        return App(pipeline, repository, logger)
    except Exception:
        if repository is not None:
            repository.close()
        logger.close()
        raise
