"""Face-crop quality gate: reject faces that would give unreliable embeddings.

A bad crop (tiny, blurry, cut off by the frame edge, low confidence) produces a
noisy embedding, and noisy embeddings are the main cause of duplicate
registrations. So we simply do not use them.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.config import QualityConfig
from app.models import BBox

SHARPNESS_SIZE = (112, 112)  # compare sharpness at a fixed size, whatever the face size


def sharpness(crop: np.ndarray) -> float:
    """Variance of the Laplacian: higher = sharper."""
    gray = crop if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, SHARPNESS_SIZE, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


@dataclass
class QualityResult:
    ok: bool
    reason: str = ""
    sharpness: float = 0.0


class QualityChecker:
    def __init__(self, cfg: QualityConfig) -> None:
        self.cfg = cfg

    def check(self, image: np.ndarray, bbox: BBox, confidence: float) -> QualityResult:
        cfg = self.cfg
        if confidence < cfg.min_detection_confidence:
            return QualityResult(False, "low_confidence")
        x1, y1, x2, y2 = bbox
        if min(x2 - x1, y2 - y1) < cfg.min_face_size_px:
            return QualityResult(False, "too_small")
        height, width = image.shape[:2]
        if cfg.reject_edge_touching and (
                x1 < cfg.edge_margin_px or y1 < cfg.edge_margin_px
                or x2 > width - cfg.edge_margin_px or y2 > height - cfg.edge_margin_px):
            return QualityResult(False, "touches_frame_edge")
        left, top = max(int(x1), 0), max(int(y1), 0)
        crop = image[top:min(int(y2), height), left:min(int(x2), width)]
        if crop.size == 0:
            return QualityResult(False, "empty_crop")
        score = sharpness(crop)
        if score < cfg.blur_threshold:
            return QualityResult(False, "too_blurry", score)
        return QualityResult(True, "", score)
