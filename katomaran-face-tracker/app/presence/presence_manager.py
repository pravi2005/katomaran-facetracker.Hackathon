"""Presence state machine: guarantees ONE ENTRY and ONE EXIT per visit.

State is keyed by **Face ID** (not Track ID), so a tracker ID switch after an
occlusion cannot create a second ENTRY.

    ABSENT --(face observed)--------------------------> PRESENT   emits ENTRY
    PRESENT --(not observed in a detection cycle)-----> MISSING    (no event)
    MISSING --(observed again before timeout)---------> PRESENT    (no event)
    MISSING --(unseen > max_missing_seconds)----------> ABSENT     emits EXIT(person_left)
    PRESENT/MISSING --(application shutdown)----------> ABSENT     emits EXIT(shutdown)

Time comes from ``FrameTime.stream_seconds`` so behaviour is identical for a
video file (video time) and for RTSP (wall time). The class is pure logic: no
database, no files, no models - which makes it easy to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np

from app.models import (EventType, ExitReason, FrameTime, Observation,
                        PresenceEvent, PresenceState)


@dataclass
class _Session:
    face_id: str
    state: PresenceState
    last_seen: float
    last_track_id: Optional[int]
    last_time: FrameTime
    last_crop: Optional[np.ndarray]


class PresenceManager:
    def __init__(self, max_missing_seconds: float) -> None:
        if max_missing_seconds <= 0:
            raise ValueError("max_missing_seconds must be > 0")
        self.max_missing_seconds = max_missing_seconds
        self._sessions: Dict[str, _Session] = {}

    # -- queries ----------------------------------------------------------
    def state_of(self, face_id: str) -> PresenceState:
        session = self._sessions.get(face_id)
        return session.state if session else PresenceState.ABSENT

    def present_face_ids(self) -> List[str]:
        return sorted(self._sessions)

    # -- updates ----------------------------------------------------------
    def update(self, now: FrameTime, observations: Iterable[Observation]) -> List[PresenceEvent]:
        """Call once per detection cycle with every identified, visible face."""
        events: List[PresenceEvent] = []

        # If two tracks resolve to the same person, keep the more confident one.
        best: Dict[str, Observation] = {}
        for obs in observations:
            if obs.face_id not in best or obs.confidence > best[obs.face_id].confidence:
                best[obs.face_id] = obs

        for face_id, obs in best.items():
            session = self._sessions.get(face_id)
            if session is None:
                self._sessions[face_id] = _Session(face_id, PresenceState.PRESENT,
                                                   now.stream_seconds, obs.track_id, now, obs.crop)
                events.append(PresenceEvent(face_id, EventType.ENTRY, now, obs.track_id,
                                            crop=obs.crop))
                continue
            session.state = PresenceState.PRESENT      # MISSING -> PRESENT: no event
            session.last_seen = now.stream_seconds
            session.last_track_id = obs.track_id
            session.last_time = now
            if obs.crop is not None:
                session.last_crop = obs.crop

        for face_id, session in self._sessions.items():
            if face_id not in best and session.state is PresenceState.PRESENT:
                session.state = PresenceState.MISSING
        return events

    def expire(self, now: FrameTime) -> List[PresenceEvent]:
        """Call every frame: emits EXIT for faces missing longer than the timeout."""
        events: List[PresenceEvent] = []
        for face_id in list(self._sessions):
            session = self._sessions[face_id]
            if session.state is not PresenceState.MISSING:
                continue
            gap = now.stream_seconds - session.last_seen
            if gap > self.max_missing_seconds:
                events.append(PresenceEvent(face_id, EventType.EXIT, now, session.last_track_id,
                                            reason=ExitReason.PERSON_LEFT, crop=session.last_crop,
                                            absent_seconds=gap))
                del self._sessions[face_id]
        return events

    def shutdown(self, now: FrameTime) -> List[PresenceEvent]:
        """Close every open session (reason=shutdown)."""
        events = [PresenceEvent(s.face_id, EventType.EXIT, now, s.last_track_id,
                                reason=ExitReason.SHUTDOWN, crop=s.last_crop,
                                absent_seconds=now.stream_seconds - s.last_seen)
                  for s in self._sessions.values()]
        self._sessions.clear()
        return sorted(events, key=lambda e: e.face_id)
