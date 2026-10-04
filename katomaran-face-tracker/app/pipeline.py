"""The per-frame processing loop. Wires every component together.

    read frame -> tracker.predict() -> (every N+1 frames) YOLO + tracker.update()
      -> resolve identity for fresh tracks -> presence update -> ENTRY/EXIT
      -> record (image + DB + log) -> display

The pipeline contains NO model, SQL or file-format code: everything it needs is
injected, so tests can run it with fake detectors/embedders (tests/test_pipeline_scenarios.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol, Sequence

import numpy as np

from app.config import AppConfig
from app.display import Display
from app.event_logging import event_logger as ev
from app.event_logging.event_logger import EventLogger
from app.input.video_source import VideoSource
from app.metrics import Metrics
from app.models import Detection, Frame, FrameTime, Observation, PresenceEvent
from app.presence.event_recorder import EventRecorder
from app.presence.presence_manager import PresenceManager
from app.presence.visitor_counter import VisitorCounter
from app.recognition.identity_resolver import IdentityResolver
from app.storage.image_store import crop_with_padding
from app.tracking.tracker import ByteTracker


class Detector(Protocol):
    def detect(self, image: np.ndarray) -> Sequence[Detection]: ...


@dataclass
class RunSummary:
    frames: int
    unique_visitors: int
    stopped_by_user: bool


class DetectionScheduler:
    """Decides which frames get a (costly) YOLO pass: every (skip_frames + 1)-th."""

    def __init__(self, skip_frames: int) -> None:
        self._interval = skip_frames + 1
        self._count = 0

    def should_detect(self) -> bool:
        detect = self._count % self._interval == 0
        self._count += 1
        return detect


class Pipeline:
    def __init__(self, cfg: AppConfig, source: VideoSource, detector: Detector,
                 tracker: ByteTracker, resolver: IdentityResolver, presence: PresenceManager,
                 recorder: EventRecorder, counter: VisitorCounter, logger: EventLogger,
                 display: Optional[Display] = None, metrics: Optional[Metrics] = None) -> None:
        self._cfg = cfg
        self._source = source
        self._detector = detector
        self._tracker = tracker
        self._resolver = resolver
        self._presence = presence
        self._recorder = recorder
        self._counter = counter
        self._log = logger
        self._display = display
        self._metrics = metrics or Metrics()
        self._scheduler = DetectionScheduler(cfg.detection.skip_frames)
        self._stop_requested = False
        self._user_quit = False

    @property
    def metrics(self) -> Metrics:
        return self._metrics

    @property
    def source(self) -> VideoSource:
        return self._source

    def request_stop(self) -> None:
        """Safe to call from a signal handler."""
        self._stop_requested = True

    def run(self, max_frames: Optional[int] = None) -> RunSummary:
        last_time: Optional[FrameTime] = None
        self._warn_if_timeout_too_short()
        try:
            while not self._stop_requested:
                if max_frames is not None and self._metrics.frames >= max_frames:
                    break
                with self._metrics.stage("read"):
                    frame = self._source.read()
                if frame is None:
                    break  # end of video file
                last_time = frame.time
                self._process_frame(frame)
                self._metrics.tick()
        finally:
            self._shutdown(last_time)
        return RunSummary(self._metrics.frames, self._counter.count, self._user_quit)

    # -- one frame --------------------------------------------------------
    def _process_frame(self, frame: Frame) -> None:
        self._tracker.predict()
        if self._scheduler.should_detect():
            self._detection_cycle(frame)
        with self._metrics.stage("presence_expire"):
            for event in self._presence.expire(frame.time):
                self._recorder.record(event)
        if self._display is not None:
            keep_going = self._display.show(frame.image, self._tracker.tracks,
                                            self._resolver.face_id_of, self._metrics.fps,
                                            self._counter.count)
            if not keep_going:
                self._user_quit = True
                self._stop_requested = True

    def _detection_cycle(self, frame: Frame) -> None:
        with self._metrics.stage("detect"):
            detections = self._detector.detect(frame.image)
        new_tracks, removed = self._tracker.update(detections, frame.time.stream_seconds)

        for track in new_tracks:
            self._log.info(ev.FACE_DETECTED, track_id=track.track_id, confidence=track.confidence)
            self._log.info(ev.TRACK_CREATED, track_id=track.track_id)
        for track in removed:
            self._log.info(ev.TRACK_LOST, track_id=track.track_id,
                           face_id=self._resolver.face_id_of(track.track_id) or "UNKNOWN")
            self._resolver.forget(track.track_id)

        observations: List[Observation] = []
        with self._metrics.stage("recognise"):
            for track in self._tracker.tracks:
                if not track.matched_this_update:
                    continue
                face_id = self._resolver.resolve(track, frame)
                if face_id is None:
                    continue
                self._counter.observe(face_id)
                crop = crop_with_padding(frame.image, track.bbox, self._cfg.storage.crop_padding_ratio)
                observations.append(Observation(face_id, track.track_id, track.confidence, crop))
        for event in self._presence.update(frame.time, observations):
            self._recorder.record(event)

    # -- shutdown ---------------------------------------------------------
    def _shutdown(self, last_time: Optional[FrameTime]) -> None:
        if last_time is not None:
            now = FrameTime(last_time.stream_seconds, datetime.now().astimezone(), last_time.source_seconds)
            events: List[PresenceEvent] = self._presence.shutdown(now)
            for event in events:
                self._recorder.record(event)
        self._recorder.flush_pending()
        for track in self._tracker.drain():
            self._resolver.forget(track.track_id)
        if self._display is not None:
            self._display.close()

    def _warn_if_timeout_too_short(self) -> None:
        fps = self._source.fps
        if fps <= 0:
            return
        interval = (self._cfg.detection.skip_frames + 1) / fps
        if interval >= self._cfg.tracking.max_missing_seconds:
            self._log.warning(ev.CONFIG_WARNING,
                              message="detection interval >= max_missing_seconds; people may get "
                                      "false EXIT events. Lower detection.skip_frames or raise "
                                      "tracking.max_missing_seconds",
                              detection_interval_seconds=interval,
                              max_missing_seconds=self._cfg.tracking.max_missing_seconds)
