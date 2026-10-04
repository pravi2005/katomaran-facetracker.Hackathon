"""Live preview window (OpenCV). Optional - disable with display.enabled=false."""

from __future__ import annotations

from typing import Callable, Optional, Sequence

import cv2
import numpy as np

from app.models import Track

GREEN, ORANGE, WHITE, BLACK = (0, 200, 0), (0, 165, 255), (255, 255, 255), (0, 0, 0)


class Display:
    def __init__(self, window_name: str) -> None:
        self._name = window_name
        self._enabled = True

    def show(self, image: np.ndarray, tracks: Sequence[Track],
             face_id_of: Callable[[int], Optional[str]], fps: float, unique_count: int) -> bool:
        """Draw and show one frame. Returns False if the user pressed 'q' / ESC."""
        if not self._enabled:
            return True
        canvas = image.copy()
        for track in tracks:
            face_id = face_id_of(track.track_id)
            colour = GREEN if face_id else ORANGE
            x1, y1, x2, y2 = (int(v) for v in track.bbox)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), colour, 2)
            label = f"{face_id or 'UNKNOWN'} | T{track.track_id} | {track.confidence:.2f}"
            self._text(canvas, label, (x1, max(y1 - 8, 14)), colour)
        self._text(canvas, f"Unique Visitors: {unique_count}   FPS: {fps:.1f}", (10, 24), WHITE)
        try:
            cv2.imshow(self._name, canvas)
            key = cv2.waitKey(1) & 0xFF
        except cv2.error:
            self._enabled = False  # headless OpenCV build / no display
            return True
        return key not in (ord("q"), 27)

    @staticmethod
    def _text(canvas: np.ndarray, text: str, origin: tuple, colour: tuple) -> None:
        cv2.putText(canvas, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.55, BLACK, 3, cv2.LINE_AA)
        cv2.putText(canvas, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.55, colour, 1, cv2.LINE_AA)

    def close(self) -> None:
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
