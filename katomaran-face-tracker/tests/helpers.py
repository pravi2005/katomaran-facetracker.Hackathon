"""Shared fakes for tests: scripted video, detector and embedder (no GPU/models needed)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.app_factory import build_tracker
from app.config import AppConfig
from app.database.sqlite_repository import SQLiteRepository
from app.event_logging.event_logger import EventLogger
from app.input.video_source import VideoSource
from app.models import BBox, Detection, Frame, FrameTime
from app.pipeline import Pipeline
from app.presence.event_recorder import EventRecorder
from app.presence.presence_manager import PresenceManager
from app.presence.visitor_counter import VisitorCounter
from app.recognition.identity_resolver import IdentityResolver
from app.recognition.quality import QualityChecker
from app.registration.face_registry import FaceRegistry
from app.storage.image_store import ImageStore
from datetime import datetime, timedelta

DIM = 64
FPS = 10.0
IMG_H, IMG_W = 240, 320
BOXES: Dict[str, BBox] = {"A": (40, 60, 120, 140), "B": (200, 60, 280, 140)}


def person_vector(name: str) -> np.ndarray:
    seed = sum(ord(c) for c in name) * 7919
    vector = np.random.default_rng(seed).normal(size=DIM).astype(np.float32)
    return vector / np.linalg.norm(vector)


def unit(v: np.ndarray) -> np.ndarray:
    return (v / np.linalg.norm(v)).astype(np.float32)


@dataclass
class Scene:
    """timeline: person -> list of (start_frame, end_frame) intervals (end exclusive)."""

    timeline: Dict[str, List[Tuple[int, int]]]
    total_frames: int
    index: int = 0

    def visible(self, index: int) -> List[str]:
        return [p for p, spans in self.timeline.items() if any(a <= index < b for a, b in spans)]


class FakeSource(VideoSource):
    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self._rng = np.random.default_rng(0)
        self._start = datetime(2026, 10, 3, 10, 0, 0).astimezone()

    def open(self) -> None: ...
    def close(self) -> None: ...

    @property
    def description(self) -> str:
        return "fake"

    @property
    def fps(self) -> float:
        return FPS

    def read(self) -> Optional[Frame]:
        i = self.scene.index
        if i >= self.scene.total_frames:
            return None
        image = self._rng.integers(0, 255, size=(IMG_H, IMG_W, 3), dtype=np.uint8)  # sharp noise
        seconds = i / FPS
        frame = Frame(image, i, FrameTime(seconds, self._start + timedelta(seconds=seconds), seconds))
        self.scene.index += 1
        return frame


class FakeDetector:
    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.calls = 0

    def detect(self, image: np.ndarray) -> Sequence[Detection]:
        self.calls += 1
        index = self.scene.index - 1  # index of the frame just read
        return [Detection(BOXES[p], 0.95) for p in self.scene.visible(index)]


class FakeEmbedder:
    model_name = "fake/model"
    embedding_dim = DIM

    def __init__(self) -> None:
        self._rng = np.random.default_rng(1)
        self.calls = 0

    def embed(self, image, bbox, landmarks):
        self.calls += 1
        centre_x = (bbox[0] + bbox[2]) / 2
        person = "A" if centre_x < IMG_W / 2 else "B"
        return unit(person_vector(person) + self._rng.normal(scale=0.01, size=DIM).astype(np.float32))


def make_config(tmp_path: Path) -> AppConfig:
    cfg = AppConfig(base_dir=tmp_path)
    cfg.detection.skip_frames = 1
    cfg.tracking.max_missing_seconds = 2.0
    cfg.tracking.track_buffer_seconds = 0.5
    cfg.recognition.embeddings_per_decision = 2
    cfg.quality.blur_threshold = 0.0
    cfg.quality.min_face_size_px = 10
    cfg.display.enabled = False
    cfg.logging.console = False
    return cfg


@dataclass
class Harness:
    pipeline: Pipeline
    repo: SQLiteRepository
    logger: EventLogger
    scene: Scene
    registry: FaceRegistry
    embedder: FakeEmbedder
    cfg: AppConfig

    def run(self):
        return self.pipeline.run()

    def close(self) -> None:
        self.repo.close()
        self.logger.close()


def build_harness(tmp_path: Path, timeline: Dict[str, List[Tuple[int, int]]], total_frames: int,
                  db_name: str = "faces.db", log_name: str = "events.log") -> Harness:
    cfg = make_config(tmp_path)
    scene = Scene(timeline, total_frames)
    logger = EventLogger(tmp_path / "logs" / log_name, console=False)
    repo = SQLiteRepository(tmp_path / db_name)
    embedder = FakeEmbedder()
    repo.ensure_embedding_compatibility(embedder.embedding_dim, embedder.model_name)
    images = ImageStore(tmp_path / "logs")
    registry = FaceRegistry.load(repo, images, logger, cfg.recognition.similarity_threshold)
    resolver = IdentityResolver(embedder, registry, QualityChecker(cfg.quality), cfg.recognition,
                                cfg.storage.crop_padding_ratio, logger)
    pipeline = Pipeline(cfg, FakeSource(scene), FakeDetector(scene), build_tracker(cfg), resolver,
                        PresenceManager(cfg.tracking.max_missing_seconds),
                        EventRecorder(repo, images, logger),
                        VisitorCounter("all_time", lambda: registry.registered_count), logger)
    return Harness(pipeline, repo, logger, scene, registry, embedder, cfg)
