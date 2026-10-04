"""Threshold calibration maths (pure NumPy, unit-tested).

Given labelled embeddings (person name -> list of embeddings) it compares
  * SAME-person similarities   (all pairs inside one group)
  * DIFFERENT-person similarities (pairs across groups)
and reports where a threshold would sit. The numbers come only from the data
you provide - they are never pre-filled.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Dict, List, Optional

import numpy as np

from app.recognition.face_matcher import normalize


@dataclass
class CalibrationReport:
    same_count: int
    different_count: int
    same_p05: float
    different_p95: float
    suggested_threshold: Optional[float]
    separable: bool


def compute_report(groups: Dict[str, List[np.ndarray]]) -> CalibrationReport:
    vectors = {name: [normalize(v) for v in items] for name, items in groups.items()}
    same = [float(a @ b) for items in vectors.values() for a, b in combinations(items, 2)]
    different = [float(a @ b)
                 for (_, ia), (_, ib) in combinations(vectors.items(), 2)
                 for a in ia for b in ib]
    if not same or not different:
        raise ValueError("Need at least two people and two images for at least one person.")
    same_p05 = float(np.percentile(same, 5))
    different_p95 = float(np.percentile(different, 95))
    separable = same_p05 > different_p95
    suggested = (same_p05 + different_p95) / 2 if separable else None
    return CalibrationReport(len(same), len(different), same_p05, different_p95, suggested, separable)
