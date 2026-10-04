# 15-20 minute revision sheet

## Architecture in one breath
Video/RTSP -> `VideoSource` -> every frame `tracker.predict()` -> every (skip+1)-th frame YOLO -> `tracker.update()` -> `IdentityResolver` (quality, embedding, average of 3) -> `FaceRegistry` (cosine vs gallery: existing or register) -> `PresenceManager` (ENTRY/EXIT) -> `EventRecorder` (image + SQLite + `events.log`) -> unique count.

## Four concepts
Detection = box now | Track ID = temporary label | Face ID = permanent identity | Presence state = per Face ID (ABSENT/PRESENT/MISSING).

## Tech
Python, OpenCV, Ultralytics YOLO (`yolov8n-face.pt`, box-only), InsightFace `buffalo_l` (ArcFace, 512-d, ONNX Runtime), own ByteTrack-style tracker (NumPy), SQLite, stdlib logging, JSON config, pytest (93 tests).

## Numbers (defaults, NOT tuned)
`skip_frames=4` (YOLO every 5th frame) | `confidence_threshold=0.5` | `similarity_threshold=0.45` | `embeddings_per_decision=3` | `max_missing_seconds=2.0` | `track_buffer_seconds=2.0` | `min_face_size_px=48` | `blur_threshold=30`.

## Recognition
Embedding -> L2 normalise -> cosine (= dot) -> `>= threshold` existing else register. Too low = false match (count low); too high = duplicates (count high). Calibrate with `scripts/calibrate_threshold.py`.

## Entry/exit
ENTRY: ABSENT->PRESENT. MISSING (no event) for up to 2 s. EXIT `person_left` after >2 s. EXIT `shutdown` on stop. Re-entry: same Face ID, new ENTRY, count unchanged.

## Database
`faces(face_id, seq, registered_at, embedding BLOB float32, representative_image_path)`, `events(event_id, face_id, event_type, timestamp, source_timestamp, image_path, track_id, reason)`, `meta`. IDs = `MAX(seq)+1` in a transaction. Count = `COUNT(*) FROM faces`. Images on disk (`logs/entries|exits|registrations/date/`).

## Resilience
WAL + transactions, atomic image writes, retry queue for events, flushed log, RTSP reconnect, config validation, graceful shutdown.

## Limitations (say them first)
Simplified tracker (no Kalman/Hungarian), identity not re-verified, one embedding per person, no liveness, presence-based events, real-model/RTSP behaviour verified only by me after running (update this line), defaults uncalibrated until I do.

## Likely questions
Why Face ID != Track ID? How do you avoid duplicate ENTRY? How is threshold chosen? Why frame skipping and its trade-off? What if DB fails? How to scale to many cameras? Privacy? What did AI do vs what did you do?

## Commands
`python -m pytest -q` | `python -m app.main --source sample.mp4 --db data/demo.db` | `python -m app.main --rtsp-env RTSP_URL` | `sqlite3 data/faces.db "SELECT COUNT(*) FROM faces;"`
