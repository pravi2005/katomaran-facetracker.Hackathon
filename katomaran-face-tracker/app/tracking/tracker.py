"""ByteTrack-style multi-face tracker (self-contained, no extra dependency).

What is implemented (and what is NOT)
-------------------------------------
Like ByteTrack, association is done in TWO stages:
  1. high-confidence detections are matched to existing tracks by IoU;
  2. leftover tracks are matched against LOW-confidence detections (these are
     often the same face, partly occluded or blurred, and would otherwise
     cause track loss).
Unmatched high-confidence detections start new tracks.

Differences from the reference ByteTrack (documented honestly):
  * motion model = damped constant velocity (not a Kalman filter);
  * assignment = greedy by descending IoU (not the Hungarian algorithm);
  * no appearance features (like ByteTrack - IDs may switch after long occlusion,
    which is why presence is keyed by Face ID, not Track ID).

Frame skipping
--------------
``predict()`` is called on EVERY frame and moves each box using its estimated
velocity ("coasting"). ``update()`` is called only on frames where YOLO ran.
The Tracker interface is tiny, so Ultralytics' BYTETracker or another tracker
can replace this class without touching the pipeline.
"""

from __future__ import annotations

from typing import Dict, List, Protocol, Sequence, Tuple

import numpy as np

from app.models import BBox, Detection, Track

VELOCITY_DECAY = 0.85       # coasting slows down so a lost box does not fly away
VELOCITY_SMOOTHING = 0.5    # blend of old and new velocity estimates


class Tracker(Protocol):
    def predict(self) -> None: ...
    def update(self, detections: Sequence[Detection], now: float) -> Tuple[List[Track], List[Track]]: ...


def iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


class _InternalTrack:
    def __init__(self, track_id: int, det: Detection, now: float) -> None:
        self.track = Track(track_id=track_id, bbox=det.bbox, confidence=det.confidence,
                           landmarks=det.landmarks, hits=1, matched_this_update=True,
                           created_at=now, last_matched_at=now)
        self.velocity = np.zeros(4, dtype=np.float64)
        self.frames_since_update = 0

    def predict(self) -> None:
        box = np.array(self.track.bbox, dtype=np.float64) + self.velocity
        self.track.bbox = tuple(float(v) for v in box)  # type: ignore[assignment]
        self.velocity *= VELOCITY_DECAY
        self.frames_since_update += 1

    def apply(self, det: Detection, now: float) -> None:
        old = np.array(self.track.bbox, dtype=np.float64)
        new = np.array(det.bbox, dtype=np.float64)
        frames = max(self.frames_since_update, 1)
        measured = (new - old) / frames
        self.velocity = VELOCITY_SMOOTHING * self.velocity + (1 - VELOCITY_SMOOTHING) * measured
        self.track.bbox = det.bbox
        self.track.confidence = det.confidence
        self.track.landmarks = det.landmarks
        self.track.hits += 1
        self.track.matched_this_update = True
        self.track.last_matched_at = now
        self.frames_since_update = 0


class ByteTracker:
    def __init__(self, high_threshold: float, low_threshold: float,
                 match_iou: float = 0.3, low_match_iou: float = 0.5,
                 buffer_seconds: float = 2.0) -> None:
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.match_iou = match_iou
        self.low_match_iou = low_match_iou
        self.buffer_seconds = buffer_seconds
        self._tracks: Dict[int, _InternalTrack] = {}
        self._next_id = 1

    @property
    def tracks(self) -> List[Track]:
        return [t.track for t in self._tracks.values()]

    def predict(self) -> None:
        """Advance every track by one frame (no detections available)."""
        for internal in self._tracks.values():
            internal.predict()
            internal.track.matched_this_update = False

    def update(self, detections: Sequence[Detection], now: float) -> Tuple[List[Track], List[Track]]:
        """Associate detections; return (new_tracks, removed_tracks)."""
        for internal in self._tracks.values():
            internal.track.matched_this_update = False

        high = [d for d in detections if d.confidence >= self.high_threshold]
        low = [d for d in detections if self.low_threshold <= d.confidence < self.high_threshold]

        track_ids = list(self._tracks)
        matches1, unmatched_tracks, unmatched_high = self._associate(track_ids, high, self.match_iou)
        for tid, det in matches1:
            self._tracks[tid].apply(det, now)
        matches2, still_unmatched, _ = self._associate(unmatched_tracks, low, self.low_match_iou)
        for tid, det in matches2:
            self._tracks[tid].apply(det, now)

        new_tracks: List[Track] = []
        for det in unmatched_high:
            internal = _InternalTrack(self._next_id, det, now)
            self._tracks[self._next_id] = internal
            new_tracks.append(internal.track)
            self._next_id += 1

        removed: List[Track] = []
        for tid in still_unmatched:
            internal = self._tracks[tid]
            if now - internal.track.last_matched_at > self.buffer_seconds:
                removed.append(internal.track)
                del self._tracks[tid]
        return new_tracks, removed

    def drain(self) -> List[Track]:
        """Remove and return every remaining track (used at shutdown)."""
        removed = self.tracks
        self._tracks.clear()
        return removed

    def _associate(self, track_ids: Sequence[int], detections: Sequence[Detection],
                   threshold: float) -> Tuple[List[Tuple[int, Detection]], List[int], List[Detection]]:
        """Greedy IoU matching. Returns (matches, unmatched_track_ids, unmatched_detections)."""
        pairs = []
        for tid in track_ids:
            for d_index, det in enumerate(detections):
                score = iou(self._tracks[tid].track.bbox, det.bbox)
                if score >= threshold:
                    pairs.append((score, tid, d_index))
        pairs.sort(reverse=True)
        used_tracks, used_dets = set(), set()
        matches: List[Tuple[int, Detection]] = []
        for _, tid, d_index in pairs:
            if tid in used_tracks or d_index in used_dets:
                continue
            used_tracks.add(tid)
            used_dets.add(d_index)
            matches.append((tid, detections[d_index]))
        unmatched_tracks = [t for t in track_ids if t not in used_tracks]
        unmatched_dets = [d for i, d in enumerate(detections) if i not in used_dets]
        return matches, unmatched_tracks, unmatched_dets
