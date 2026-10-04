# Project overview (based on the final code in `katomaran-face-tracker/`)

## 30-second explanation
"It's a Python system that watches a video or an RTSP camera, finds faces with a YOLO face model, tracks them, recognises each person with InsightFace/ArcFace embeddings, and registers anyone new as F001, F002 and so on. For every visit it logs exactly one ENTRY and one EXIT with a cropped photo and timestamp into SQLite and `events.log`, and it keeps a unique visitor count that doesn't go up when the same person comes back."

## 1-minute explanation
Add: "The key design idea is that I keep four things separate: a *detection* is one box in one frame, a *Track ID* is the tracker's temporary label, a *Face ID* is the permanent identity from the embedding match, and *presence state* belongs to the Face ID. Because ENTRY and EXIT are driven by a small state machine keyed by Face ID with a time-based timeout, a missed detection or a tracker ID switch can't create duplicate events. To save compute, YOLO runs only every N+1 frames (configurable) and the tracker coasts in between, and embeddings are computed only for tracks that don't have an identity yet."

## 3-minute explanation
1. **Input:** a `VideoSource` interface with `FileVideoSource` and `RTSPVideoSource`, so the pipeline never cares about the source. RTSP uses a reader thread that keeps only the newest frame and reconnects.
2. **Detect + track:** YOLO face model (`yolov8n-face.pt`) every `skip_frames+1` frames; my ByteTrack-style tracker associates boxes in two stages (high then low confidence) and predicts motion on skipped frames.
3. **Identity:** for a new track I run a quality gate (size, blur, edge, confidence), generate InsightFace embeddings, average three, and compare with cosine similarity to the stored gallery. At or above `similarity_threshold` (0.45 starting value, to be calibrated) it's an existing person; otherwise a new Face ID is created by the database (`MAX(seq)+1`), with embedding, image and metadata.
4. **Presence:** `PresenceManager` has ABSENT/PRESENT/MISSING per Face ID. ENTRY only on ABSENT→PRESENT, EXIT only after `max_missing_seconds` (2.0 s) absence, or `shutdown` on stop. Re-entry gives a new ENTRY but the same Face ID, so the count doesn't change.
5. **Persistence:** SQLite (`faces`, `events`, `meta`), images under `logs/entries|exits|registrations/date/`, structured `events.log`. Writes are transactional, images atomic, DB failures queued and retried.
6. **Quality:** 93 automated tests run the full pipeline; real YOLO face detection, InsightFace ArcFace (512-d), and real MP4 video processing have been verified end-to-end on CPU (~16.9 FPS).

## Detailed explanation
Read in order: `ARCHITECTURE_EXPLANATION.md`, `ENTRY_EXIT_LOGIC.md`, `DATABASE_EXPLANATION.md`, `CODE_EXPLANATION.md`.

## Facts you must be able to state accurately
- Tracker is **ByteTrack-style, self-written**: two-stage association kept, Kalman filter and Hungarian assignment replaced by damped constant velocity and greedy IoU matching.
- YOLO model is **box-only**; landmarks come from InsightFace's own detector on a padded crop (extra cost, only for unresolved tracks).
- Threshold 0.45, skip_frames 4, confidence 0.5 are **starting values**, calibrated as needed.
- Measured real-video performance on CPU: ~16.9 FPS (with skip_frames=4 on 4K video).
- Real YOLO, InsightFace (512-d), and MP4 video have been verified end-to-end; live physical RTSP camera remains unverified (tested via mock capture).
