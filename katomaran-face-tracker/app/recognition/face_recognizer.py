"""InsightFace (ArcFace) embedding generator.

Model pack: ``buffalo_l`` by default (SCRFD detector + ArcFace ResNet50 trained
on WebFace600K, 512-d embeddings). The embedding dimension is NOT hard-coded:
it is measured by running a dummy image through the model at start-up.

Two ways to get an aligned face:
  A) detector supplied 5 landmarks -> align with ``norm_crop`` -> embed (cheap)
  B) no landmarks (default YOLO face model) -> run InsightFace's own SCRFD on a
     padded crop to find landmarks, then embed (extra model call; only done for
     unresolved tracks, never every frame)

NOT VERIFIED in the build environment (needs the real model + GPU/CPU runtime).
InsightFace models are for non-commercial research use - see README.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from app.errors import ModelLoadError, RecognitionError
from app.models import BBox
from app.recognition.face_matcher import normalize
from app.storage.image_store import crop_with_padding

ALIGNED_SIZE = 112
FALLBACK_PADDING = 0.3
FALLBACK_DET_SIZE = (320, 320)


def _select_providers() -> tuple[List[str], int]:
    """Prefer CUDA when onnxruntime-gpu is installed, otherwise CPU."""
    try:
        import onnxruntime
    except ImportError as exc:
        raise ModelLoadError("onnxruntime is not installed (pip install -r requirements.txt).") from exc
    available = onnxruntime.get_available_providers()
    if "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"], 0
    return ["CPUExecutionProvider"], -1


class InsightFaceEmbedder:
    def __init__(self, model_pack: str = "buffalo_l") -> None:
        try:
            from insightface.app import FaceAnalysis
            from insightface.utils import face_align
        except ImportError as exc:
            raise ModelLoadError("The 'insightface' package is not installed. "
                                 "See README (Windows may need C++ Build Tools).") from exc
        providers, ctx_id = _select_providers()
        try:
            self._app = FaceAnalysis(name=model_pack, allowed_modules=["detection", "recognition"],
                                     providers=providers)
            self._app.prepare(ctx_id=ctx_id, det_size=FALLBACK_DET_SIZE)
            self._rec = self._app.models["recognition"]
        except Exception as exc:  # noqa: BLE001 - insightface raises assorted errors (download, onnx...)
            raise ModelLoadError(f"Could not load InsightFace pack '{model_pack}': {exc}") from exc
        self._norm_crop = face_align.norm_crop
        self.model_name = f"insightface/{model_pack}"
        self.device = "cuda" if ctx_id >= 0 else "cpu"
        probe = self._rec.get_feat(np.zeros((ALIGNED_SIZE, ALIGNED_SIZE, 3), dtype=np.uint8))
        self.embedding_dim = int(np.asarray(probe).reshape(-1).shape[0])

    def embed(self, image: np.ndarray, bbox: BBox,
              landmarks: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Return a normalised embedding, or None if no usable face was found."""
        try:
            if landmarks is not None:
                aligned = self._norm_crop(image, landmark=landmarks.astype(np.float32),
                                          image_size=ALIGNED_SIZE)
                vector = self._rec.get_feat(aligned)
            else:
                vector = self._embed_via_insightface_detector(image, bbox)
        except Exception as exc:  # noqa: BLE001 - onnxruntime/opencv errors vary
            raise RecognitionError(f"Embedding failed: {exc}") from exc
        if vector is None:
            return None
        return normalize(np.asarray(vector))

    def _embed_via_insightface_detector(self, image: np.ndarray, bbox: BBox) -> Optional[np.ndarray]:
        crop = crop_with_padding(image, bbox, FALLBACK_PADDING)
        if crop is None:
            return None
        faces = self._app.get(crop)
        if not faces:
            return None
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.embedding
