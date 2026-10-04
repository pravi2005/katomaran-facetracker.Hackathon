"""Video input abstraction: the pipeline only sees ``VideoSource.read()``.

    VideoSource (abstract)
    |-- FileVideoSource   local MP4/AVI/... (stream clock = video time)
    `-- RTSPVideoSource   live stream, background reader thread that always
                          keeps only the NEWEST frame (so slow processing does
                          not make you analyse stale video) and reconnects.

read() returns a Frame, or None at the end of a file. Unrecoverable problems
raise SourceError. Invalid frames (None / zero-size) are skipped.
"""

from __future__ import annotations

import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from app.config import redact_url
from app.errors import SourceError
from app.event_logging import event_logger as ev
from app.event_logging.event_logger import EventLogger
from app.models import Frame, FrameTime

MAX_CONSECUTIVE_INVALID_FRAMES = 30


def is_valid_frame(image: Optional[np.ndarray]) -> bool:
    return image is not None and isinstance(image, np.ndarray) and image.size > 0 and image.ndim == 3


class VideoSource(ABC):
    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> Optional[Frame]: ...

    @abstractmethod
    def close(self) -> None: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def fps(self) -> float:
        """Nominal frames per second (0.0 if unknown)."""
        return 0.0

    def __enter__(self) -> "VideoSource":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


class FileVideoSource(VideoSource):
    def __init__(self, path: Path,
                 capture_factory: Callable[[str], "cv2.VideoCapture"] = cv2.VideoCapture) -> None:
        self._path = path
        self._factory = capture_factory
        self._cap = None
        self._fps = 0.0
        self._index = 0

    @property
    def description(self) -> str:
        return f"video file {self._path.name}"

    @property
    def fps(self) -> float:
        return self._fps

    def open(self) -> None:
        if not self._path.is_file():
            raise SourceError(f"Video file not found: {self._path}")
        cap = self._factory(str(self._path))
        if not cap.isOpened():
            cap.release()
            raise SourceError(f"OpenCV cannot open video (corrupt or unsupported codec?): {self._path}")
        self._cap = cap
        fps = cap.get(cv2.CAP_PROP_FPS)
        self._fps = float(fps) if fps and fps > 0 else 0.0
        self._index = 0

    def read(self) -> Optional[Frame]:
        if self._cap is None:
            raise SourceError("FileVideoSource.read() called before open().")
        invalid = 0
        while True:
            ok, image = self._cap.read()
            if not ok:
                return None  # end of file
            if is_valid_frame(image):
                break
            invalid += 1
            if invalid >= MAX_CONSECUTIVE_INVALID_FRAMES:
                raise SourceError(f"{invalid} consecutive invalid frames in {self._path.name}.")
        if self._fps > 0:
            seconds = self._index / self._fps
        else:
            seconds = max(self._cap.get(cv2.CAP_PROP_POS_MSEC), 0.0) / 1000.0
        frame = Frame(image=image, index=self._index,
                      time=FrameTime(stream_seconds=seconds, wall_time=datetime.now().astimezone(),
                                     source_seconds=seconds))
        self._index += 1
        return frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class RTSPVideoSource(VideoSource):
    def __init__(self, url: str, logger: EventLogger, reconnect_max_attempts: int = 10,
                 reconnect_delay_seconds: float = 2.0, read_timeout_seconds: float = 10.0,
                 capture_factory: Callable[[str], "cv2.VideoCapture"] = cv2.VideoCapture) -> None:
        self._url = url
        self._safe_url = redact_url(url)  # never log credentials
        self._log = logger
        self._max_attempts = reconnect_max_attempts
        self._delay = reconnect_delay_seconds
        self._timeout = read_timeout_seconds
        self._factory = capture_factory
        self._cond = threading.Condition()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._latest: Optional[np.ndarray] = None
        self._latest_wall: Optional[datetime] = None
        self._latest_counter = 0
        self._returned_counter = 0
        self._fatal: Optional[SourceError] = None
        self._start = 0.0
        self._fps = 0.0
        self._index = 0

    @property
    def description(self) -> str:
        return f"RTSP stream {self._safe_url}"

    @property
    def fps(self) -> float:
        return self._fps

    def open(self) -> None:
        # TCP is more reliable than UDP over Wi-Fi/VPN. Harmless if already set.
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        cap = self._connect()
        if cap is None:
            raise SourceError(f"Cannot connect to {self._safe_url} after "
                              f"{self._max_attempts + 1} attempt(s).")
        self._start = time.monotonic()
        self._thread = threading.Thread(target=self._reader_loop, args=(cap,),
                                        name="rtsp-reader", daemon=True)
        self._thread.start()

    def _connect(self) -> Optional["cv2.VideoCapture"]:
        for attempt in range(self._max_attempts + 1):
            if self._stop.is_set():
                return None
            cap = self._factory(self._url)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                self._fps = float(fps) if fps and fps > 0 else self._fps
                return cap
            cap.release()
            self._log.error(ev.RTSP_ERROR, message="connect_failed", url=self._safe_url,
                            attempt=f"{attempt + 1}/{self._max_attempts + 1}")
            if attempt < self._max_attempts:
                self._stop.wait(self._delay)
        return None

    def _reader_loop(self, cap: "cv2.VideoCapture") -> None:
        invalid = 0
        while not self._stop.is_set():
            ok, image = cap.read()
            if ok and is_valid_frame(image):
                invalid = 0
                with self._cond:
                    self._latest, self._latest_wall = image, datetime.now().astimezone()
                    self._latest_counter += 1
                    self._cond.notify_all()
                continue
            invalid += 1
            if ok and invalid < MAX_CONSECUTIVE_INVALID_FRAMES:
                continue  # a corrupt frame - skip it
            self._log.error(ev.RTSP_ERROR, message="stream_lost", url=self._safe_url)
            cap.release()
            cap = self._connect()
            if cap is None:
                with self._cond:
                    self._fatal = SourceError(f"RTSP stream {self._safe_url} lost and could not be re-opened.")
                    self._cond.notify_all()
                return
            self._log.info(ev.RTSP_ERROR, message="reconnected", url=self._safe_url)
            invalid = 0
        cap.release()

    def read(self) -> Optional[Frame]:
        stalls = 0
        with self._cond:
            while True:
                if self._fatal is not None:
                    raise self._fatal
                if self._stop.is_set():
                    return None
                if self._latest_counter > self._returned_counter:
                    break
                if not self._cond.wait(timeout=self._timeout):
                    stalls += 1
                    self._log.error(ev.RTSP_ERROR, message="no_frames", waited_seconds=self._timeout)
                    if stalls > self._max_attempts:
                        raise SourceError(f"No frames from {self._safe_url} for "
                                          f"{stalls * self._timeout:.0f}s.")
            image, wall = self._latest, self._latest_wall
            self._returned_counter = self._latest_counter
        seconds = time.monotonic() - self._start
        frame = Frame(image=image, index=self._index,
                      time=FrameTime(stream_seconds=seconds, wall_time=wall, source_seconds=None))
        self._index += 1
        return frame

    def close(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
