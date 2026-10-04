"""Saves face images into the structured ``logs/`` directory.

    <root>/entries/YYYY-MM-DD/F001_20261003T103015_120.jpg
    <root>/exits/YYYY-MM-DD/F001_...jpg
    <root>/registrations/YYYY-MM-DD/F001.jpg

The database stores the *relative* path (posix style) of each image, not the
image bytes. Face IDs are validated before being used in a filename, which
prevents path-traversal tricks such as ``../../x``.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from app.errors import ImageStorageError

FACE_ID_PATTERN = re.compile(r"^F\d{3,}$")


def format_face_id(sequence: int) -> str:
    """1 -> 'F001', 1234 -> 'F1234'."""
    return f"F{sequence:03d}"


def crop_with_padding(image: np.ndarray, bbox: Tuple[float, float, float, float],
                      padding_ratio: float = 0.0) -> np.ndarray | None:
    """Crop ``bbox`` (x1,y1,x2,y2) from image with optional padding; None if empty."""
    height, width = image.shape[:2]
    x1, y1, x2, y2 = bbox
    pad_x = (x2 - x1) * padding_ratio
    pad_y = (y2 - y1) * padding_ratio
    left, top = max(int(x1 - pad_x), 0), max(int(y1 - pad_y), 0)
    right, bottom = min(int(x2 + pad_x), width), min(int(y2 + pad_y), height)
    if right <= left or bottom <= top:
        return None
    return image[top:bottom, left:right].copy()


class ImageStore:
    def __init__(self, root: Path, jpeg_quality: int = 90) -> None:
        self.root = root
        self.jpeg_quality = jpeg_quality
        for sub in ("entries", "exits", "registrations"):
            try:
                (root / sub).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ImageStorageError(f"Cannot create {root / sub}: {exc}") from exc

    # -- public API -------------------------------------------------------
    def save_registration(self, face_id: str, image: np.ndarray, when: datetime) -> str:
        return self._save("registrations", face_id, image, when, timestamped=False)

    def save_entry(self, face_id: str, image: np.ndarray, when: datetime) -> str:
        return self._save("entries", face_id, image, when, timestamped=True)

    def save_exit(self, face_id: str, image: np.ndarray, when: datetime) -> str:
        return self._save("exits", face_id, image, when, timestamped=True)

    # -- internals --------------------------------------------------------
    def _save(self, kind: str, face_id: str, image: np.ndarray,
              when: datetime, timestamped: bool) -> str:
        if not FACE_ID_PATTERN.match(face_id):
            raise ImageStorageError(f"Refusing unsafe face_id for filename: {face_id!r}")
        if image is None or image.size == 0:
            raise ImageStorageError(f"Empty image for {face_id}; nothing to save.")

        local = when.astimezone()
        folder = self.root / kind / local.strftime("%Y-%m-%d")
        stem = face_id
        if timestamped:
            stem += local.strftime("_%Y%m%dT%H%M%S_") + f"{local.microsecond // 1000:03d}"
        path = folder / f"{stem}.jpg"
        counter = 1
        while path.exists() and timestamped:  # avoid overwriting in same millisecond
            path = folder / f"{stem}_{counter}.jpg"
            counter += 1

        ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if not ok:
            raise ImageStorageError(f"JPEG encoding failed for {face_id}.")
        try:
            folder.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(encoded.tobytes())
            tmp.replace(path)  # atomic: a crash never leaves a half-written .jpg
        except OSError as exc:
            raise ImageStorageError(f"Cannot write {path}: {exc}") from exc
        return path.relative_to(self.root).as_posix()
