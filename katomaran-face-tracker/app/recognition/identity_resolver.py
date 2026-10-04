"""Per-track identity resolution: Track ID -> Face ID.

A track starts UNKNOWN. On each detection cycle where the track was matched to a
fresh detection we:

  1. run the quality gate (skip bad crops);
  2. generate one embedding (cached state lives in this object, per track);
  3. once ``embeddings_per_decision`` good embeddings are collected, average
     them (one blurry frame cannot create a false identity) and ask the
     FaceRegistry to identify-or-register.

After resolution the track keeps its Face ID and NO further embeddings are
computed for it (the main CPU/GPU saving). If a track cannot be resolved within
``max_resolve_attempts`` cycles it stays UNKNOWN and is never registered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

import numpy as np

from app.config import RecognitionConfig
from app.errors import DatabaseError, RecognitionError
from app.event_logging import event_logger as ev
from app.event_logging.event_logger import EventLogger
from app.models import BBox, Frame, Track
from app.recognition.face_matcher import normalize
from app.recognition.quality import QualityChecker, sharpness
from app.registration.face_registry import FaceRegistry
from app.storage.image_store import crop_with_padding


class Embedder(Protocol):
    """Anything that turns a face in a frame into an embedding (InsightFace, or a fake in tests)."""

    model_name: str
    embedding_dim: int

    def embed(self, image: np.ndarray, bbox: BBox,
              landmarks: Optional[np.ndarray]) -> Optional[np.ndarray]: ...


@dataclass
class _TrackIdentity:
    face_id: Optional[str] = None
    embeddings: List[np.ndarray] = field(default_factory=list)
    best_crop: Optional[np.ndarray] = None
    best_sharpness: float = -1.0
    attempts: int = 0
    gave_up: bool = False


class IdentityResolver:
    def __init__(self, embedder: Embedder, registry: FaceRegistry, quality: QualityChecker,
                 cfg: RecognitionConfig, crop_padding_ratio: float, logger: EventLogger) -> None:
        self._embedder = embedder
        self._registry = registry
        self._quality = quality
        self._cfg = cfg
        self._padding = crop_padding_ratio
        self._log = logger
        self._states: Dict[int, _TrackIdentity] = {}

    def face_id_of(self, track_id: int) -> Optional[str]:
        state = self._states.get(track_id)
        return state.face_id if state else None

    def forget(self, track_id: int) -> None:
        self._states.pop(track_id, None)

    def resolve(self, track: Track, frame: Frame) -> Optional[str]:
        state = self._states.setdefault(track.track_id, _TrackIdentity())
        if state.face_id is not None:
            return state.face_id
        if state.gave_up:
            return None

        state.attempts += 1
        if state.attempts > self._cfg.max_resolve_attempts:
            state.gave_up = True
            self._log.warning(ev.RECOGNITION_FAILED, track_id=track.track_id,
                              reason="max_resolve_attempts_exceeded")
            return None

        quality = self._quality.check(frame.image, track.bbox, track.confidence)
        if not quality.ok:
            return None  # per-frame rejections are intentionally not logged (too noisy)

        try:
            embedding = self._embedder.embed(frame.image, track.bbox, track.landmarks)
            if embedding is None:
                return None
            embedding = normalize(embedding)
        except RecognitionError as exc:
            self._log.warning(ev.RECOGNITION_FAILED, track_id=track.track_id, error=str(exc))
            return None
        self._log.info(ev.EMBEDDING_GENERATED, track_id=track.track_id,
                       dim=int(embedding.shape[0]), collected=len(state.embeddings) + 1)

        state.embeddings.append(embedding)
        crop = crop_with_padding(frame.image, track.bbox, self._padding)
        if crop is not None:
            score = sharpness(crop)
            if score > state.best_sharpness:
                state.best_sharpness, state.best_crop = score, crop

        if len(state.embeddings) < self._cfg.embeddings_per_decision:
            return None
        return self._decide(track, frame, state)

    def _decide(self, track: Track, frame: Frame, state: _TrackIdentity) -> Optional[str]:
        mean_embedding = normalize(np.mean(np.stack(state.embeddings), axis=0))
        try:
            result = self._registry.identify_or_register(
                mean_embedding, state.best_crop, frame.time.wall_time, track.track_id)
        except (DatabaseError, RecognitionError) as exc:
            self._log.error(ev.DATABASE_ERROR, operation="identify_or_register",
                            track_id=track.track_id, error=str(exc))
            return None  # keep the collected embeddings and retry next cycle
        state.face_id = result.face_id
        state.embeddings.clear()
        state.best_crop = None
        if not result.is_new:
            self._log.info(ev.FACE_RECOGNIZED, face_id=result.face_id,
                           track_id=track.track_id, similarity=result.similarity)
        return result.face_id
