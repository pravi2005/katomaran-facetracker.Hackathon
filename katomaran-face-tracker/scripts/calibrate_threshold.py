"""Calibrate recognition.similarity_threshold on YOUR data.

Folder layout (crops of faces, e.g. copied from logs/entries/ and sorted by hand):

    calibration_faces/
        alice/  a1.jpg a2.jpg ...
        bob/    b1.jpg b2.jpg ...

Run:
    python scripts/calibrate_threshold.py calibration_faces

Needs the real InsightFace model (NOT VERIFIED in the build environment).
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.errors import AppError  # noqa: E402
from app.recognition.calibration import compute_report  # noqa: E402
from app.recognition.face_recognizer import InsightFaceEmbedder  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    try:
        embedder = InsightFaceEmbedder()
    except AppError as exc:
        print(f"ERROR: {exc}")
        return 2
    groups = {}
    for person in sorted(p for p in root.iterdir() if p.is_dir()):
        vectors = []
        for path in sorted(person.glob("*.jpg")) + sorted(person.glob("*.png")):
            image = cv2.imread(str(path))
            if image is None:
                print(f"skip unreadable image: {path}")
                continue
            height, width = image.shape[:2]
            vector = embedder.embed(image, (0.0, 0.0, float(width), float(height)), None)
            if vector is None:
                print(f"no face found in {path}")
                continue
            vectors.append(vector)
        groups[person.name] = vectors
        print(f"{person.name}: {len(vectors)} usable images")
    try:
        report = compute_report({k: v for k, v in groups.items() if v})
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"\nsame-person pairs: {report.same_count}, different-person pairs: {report.different_count}")
    print(f"5th percentile of SAME-person similarity:      {report.same_p05:.3f}")
    print(f"95th percentile of DIFFERENT-person similarity: {report.different_p95:.3f}")
    if report.separable:
        print(f"Distributions are separable. Suggested threshold (midpoint): {report.suggested_threshold:.3f}")
    else:
        print("Distributions OVERLAP: no clean threshold exists for this data. "
              "Improve crop quality (size/sharpness) or use more embeddings per decision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
