# Computer vision study notes (with examples from this project)

| Concept | Plain explanation | In our app |
|---|---|---|
| **Image** | grid of pixels; OpenCV stores it as a NumPy array `(height, width, 3)` in BGR order | `Frame.image` |
| **Frame** | one image from a video; video = frames at N per second | `Frame(index, time)`; file time = `index/fps` |
| **Bounding box** | rectangle `(x1, y1, x2, y2)` around an object | `Detection.bbox`, drawn in `display.py` |
| **Confidence** | model's score (0-1) that the box is really a face | `detection.confidence_threshold = 0.5` |
| **Detection** | finding *where* faces are in one frame; knows nothing about who | YOLO face model |
| **Tracking** | linking detections across frames so "the same box" keeps one label | `ByteTracker` |
| **Track ID** | the tracker's temporary label (17) | can change after occlusion |
| **Face recognition** | deciding *who* a face is | embeddings + cosine similarity |
| **Embedding** | a vector of numbers (512 for `buffalo_l`) that describes a face so similar faces give similar vectors | `InsightFaceEmbedder` |
| **Cosine similarity** | angle-based similarity of two vectors, -1..1; for unit vectors it's the dot product | `FaceMatcher.best_match` |
| **Threshold** | cut-off turning a similarity into "same / different" | `similarity_threshold = 0.45` (starting value) |
| **False positive** | system says "same person" (or "face") when it is not | two people share a Face ID (threshold too low) |
| **False negative** | system misses a true match | one person gets two IDs (threshold too high) -> count too high |
| **Occlusion** | face hidden by an object/person | tracker coasts; presence stays MISSING until `max_missing_seconds` |
| **FPS** | frames processed per second | measured, never assumed (`metrics.py`) |
| **Frame skipping** | running the expensive detector only every N+1 frames | `detection.skip_frames = 4` -> YOLO on frames 0, 5, 10 ... |
| **IoU** | overlap of two boxes: intersection / union | tracker association |
| **Blur (Laplacian variance)** | sharp images have strong edges -> large variance | `quality.py` |
| **Face alignment** | rotating/scaling a face so eyes/nose/mouth sit at standard positions before embedding | `norm_crop` to 112x112 |

## Mini examples
- *Skipping:* with `skip_frames=4` at 25 fps YOLO runs 5 times per second; in between, the tracker moves boxes using their last velocity.
- *IoU:* a box that moved a little overlaps its old position strongly (IoU near 1) -> same track; a box far away has IoU 0 -> new track.
- *Threshold:* similarity 0.62 -> same person; 0.12 -> different; 0.43 is the danger zone near 0.45 - hence averaging 3 embeddings and calibration.
