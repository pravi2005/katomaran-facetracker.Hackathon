"""YOLO face detector (Ultralytics).

Model choice
------------
A FACE-specific model is required: generic COCO YOLO weights detect 'person',
not faces. Default: ``yolov8n-face.pt`` (YOLOv8-nano trained on WIDER FACE),
published by https://github.com/akanametov/yolo-face - loadable with stock
Ultralytics, box-only (no landmarks), small/fast.

Licensing: the Ultralytics library is AGPL-3.0 and the face-model repository
is GPL-3.0. Fine for a hackathon prototype; verify before commercial use.

The model file is NOT bundled. Put it at the path in config.json
(``detection.model``). See README "Download the YOLO face model".
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import numpy as np

from app.errors import ModelLoadError
from app.models import Detection

MODEL_HELP = (
    "Download a YOLO FACE model (e.g. yolov8n-face.pt from "
    "https://github.com/akanametov/yolo-face - see its releases/README for the "
    "download link) and set detection.model in config.json to its path."
)


def resolve_device(requested: str) -> str:
    """'auto' -> first CUDA GPU if PyTorch can see one, otherwise CPU."""
    if requested != "auto":
        return requested
    try:
        import torch  # imported lazily: only needed when running real inference
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


class YoloFaceDetector:
    def __init__(self, model_path: Path, min_confidence: float, device: str = "auto",
                 image_size: int = 640) -> None:
        if not str(model_path).strip() or str(model_path) in (".", ""):
            raise ModelLoadError(f"detection.model is empty. {MODEL_HELP}")
        if not model_path.is_file():
            raise ModelLoadError(f"YOLO model file not found: {model_path}. {MODEL_HELP}")
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ModelLoadError("The 'ultralytics' package is not installed "
                                 "(pip install -r requirements.txt).") from exc
        try:
            self._model = YOLO(str(model_path))
        except Exception as exc:  # noqa: BLE001 - third-party loader raises many error types
            raise ModelLoadError(f"Could not load YOLO model {model_path}: {exc}") from exc
        self.device = resolve_device(device)
        self.min_confidence = min_confidence
        self.image_size = image_size

    def detect(self, image: np.ndarray) -> List[Detection]:
        """Return all faces with confidence >= min_confidence (low-score ones feed the tracker)."""
        result = self._model.predict(image, conf=self.min_confidence, imgsz=self.image_size,
                                     device=self.device, verbose=False)[0]
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        landmarks = self._extract_landmarks(result, len(conf))
        return [Detection(bbox=tuple(float(v) for v in xyxy[i]),  # type: ignore[arg-type]
                          confidence=float(conf[i]),
                          landmarks=None if landmarks is None else landmarks[i])
                for i in range(len(conf))]

    @staticmethod
    def _extract_landmarks(result, count: int) -> Optional[np.ndarray]:
        keypoints = getattr(result, "keypoints", None)
        if keypoints is None:
            return None
        points = keypoints.xy.cpu().numpy()
        if points.ndim == 3 and points.shape[0] == count and points.shape[1:] == (5, 2):
            return points
        return None
