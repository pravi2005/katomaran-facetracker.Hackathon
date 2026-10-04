"""Plain data containers shared between modules.

Keeping these in one small file makes the data flow of the pipeline easy to
read: Frame -> Detection -> Track -> Observation -> PresenceEvent.

Important vocabulary (never mix these up):
    Detection  - where YOLO found a face in ONE frame (no identity).
    Track ID   - the tracker's label for "same box over time". Can change.
    Face ID    - the permanent identity (F001, F002, ...). Set by recognition.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

import numpy as np

BBox = Tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


@dataclass(frozen=True)
class FrameTime:
    """All the clocks attached to one frame.

    stream_seconds:  monotonic seconds used for timeouts. For video files this
                     is the position inside the video (so results do not
                     depend on how fast we process). For RTSP it is wall time.
    wall_time:       real local time when the frame was processed.
    source_seconds:  position inside the source video, None for live streams.
    """

    stream_seconds: float
    wall_time: datetime
    source_seconds: Optional[float] = None


@dataclass
class Frame:
    image: np.ndarray
    index: int
    time: FrameTime


@dataclass
class Detection:
    bbox: BBox
    confidence: float
    landmarks: Optional[np.ndarray] = None  # (5, 2) if the detector gives them


@dataclass
class Track:
    track_id: int
    bbox: BBox
    confidence: float
    landmarks: Optional[np.ndarray] = None
    hits: int = 1
    matched_this_update: bool = True
    created_at: float = 0.0
    last_matched_at: float = 0.0


class PresenceState(enum.Enum):
    ABSENT = "ABSENT"
    PRESENT = "PRESENT"
    MISSING = "MISSING"


class EventType(str, enum.Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class ExitReason(str, enum.Enum):
    PERSON_LEFT = "person_left"
    SHUTDOWN = "shutdown"


@dataclass
class Observation:
    """'Face F003 is visible right now, seen through track 12'."""

    face_id: str
    track_id: int
    confidence: float
    crop: Optional[np.ndarray] = None


@dataclass
class PresenceEvent:
    face_id: str
    event_type: EventType
    time: FrameTime
    track_id: Optional[int]
    reason: Optional[ExitReason] = None
    crop: Optional[np.ndarray] = field(default=None, repr=False)
    absent_seconds: Optional[float] = None


@dataclass
class FaceRecord:
    face_id: str
    registered_at: str
    embedding: np.ndarray = field(repr=False)
    representative_image_path: Optional[str]


@dataclass
class EventRecord:
    event_id: int
    face_id: str
    event_type: str
    timestamp: str
    source_timestamp: Optional[str]
    image_path: Optional[str]
    track_id: Optional[int]
    reason: Optional[str]


def format_source_timestamp(seconds: Optional[float]) -> Optional[str]:
    """Format seconds as HH:MM:SS.mmm (None stays None)."""
    if seconds is None:
        return None
    total_ms = int(round(max(seconds, 0.0) * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def format_wall_time(moment: datetime) -> str:
    """ISO-8601 local time with UTC offset, millisecond precision."""
    return moment.astimezone().isoformat(timespec="milliseconds")
