# Katomaran Intelligent Face Tracker with Auto-Registration and Visitor Counting

A modular Python pipeline that watches a video file or a live RTSP camera, **detects faces (YOLO)**, **tracks them (ByteTrack-style)**, **recognises people (InsightFace / ArcFace)**, **auto-registers unseen faces** (F001, F002, ...), generates exactly **one ENTRY and one EXIT per visit**, stores everything in **SQLite + local images + `events.log`**, and maintains an accurate **unique visitor count**.

> **Verification status.** The entire pipeline is verified end-to-end: 93 automated tests pass, the real YOLO face detector (`yolov8n-face.pt`) and InsightFace ArcFace (`buffalo_l`, 512-d) models run on CPU, and a real MP4 video run verified face detection, tracking, auto-registration, ENTRY/EXIT logging, SQLite persistence, and visitor counting (~16.9 FPS CPU). Live RTSP with a physical camera remains unverified (tested via simulated reconnect/error tests). See [docs/REQUIREMENTS_MATRIX.md](docs/REQUIREMENTS_MATRIX.md).

## 1. Problem statement

Katomaran Hackathon: build an AI-driven application that processes a video stream, detects and recognises faces, automatically registers new faces, tracks them across frames, logs every entry and exit with a cropped face image and timestamp, and counts **unique** visitors. Constraints: YOLO-based detection, InsightFace/ArcFace (or similar) recognition, **no** Python `face_recognition` library, configurable frame skipping through `config.json`, mandatory `events.log`.

## 2. Objective

Provide a clear, testable, restart-safe prototype whose architecture can be explained end to end.

## 3. Features

- One input interface for **MP4/local video** and **RTSP** (threaded newest-frame reader, reconnect with retry limit, credentials never logged).
- Configurable **detection frame skipping**; tracker "coasts" between YOLO frames.
- **Track ID vs Face ID** kept strictly separate (a Track ID may change; a Face ID is permanent).
- Quality gate (size, blur, edge, confidence) + averaging of several embeddings before any identity decision.
- Auto-registration with **database-generated** IDs; embeddings stored as float32 BLOB with model/dimension validation.
- **Presence state machine** keyed by Face ID: `ABSENT -> PRESENT -> MISSING -> (EXIT)`; timeout in **seconds** (`tracking.max_missing_seconds`).
- EXIT reasons: `person_left` or `shutdown`.
- Wall-clock **and** source-video timestamps.
- Resilient writes: atomic image writes, SQLite WAL + transactions, in-memory retry queue if the DB is busy, line-flushed log file.
- Live preview: box, confidence, Track ID, Face ID (or `UNKNOWN`), FPS, unique visitors.
- Measured per-stage timing (no invented numbers).

## 4. Architecture

```
Video file / RTSP
      |  VideoSource.read()  (FileVideoSource | RTSPVideoSource)
      v
Detection Scheduler  (every skip_frames+1 frames)
      v
YOLO face detection ---------------------------+
      v                                         |  frames without YOLO:
ByteTracker.update()  <--- Track IDs            |  tracker.predict() coasts boxes
      v
IdentityResolver: crop -> quality gate -> InsightFace embedding (x N, averaged)
      v
FaceRegistry: cosine similarity vs gallery
      |-- >= threshold --> existing Face ID
      `-- <  threshold --> register new Face ID (DB-generated)
      v
PresenceManager (state machine)  --> ENTRY / EXIT events
      v
EventRecorder --> face image (logs/entries|exits|registrations)
              --> SQLite (faces, events)
              --> logs/events.log
      v
VisitorCounter --> unique_visitor_count
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 5. Technology stack

Python 3.11/3.12/3.13 (3.13.2 verified) | OpenCV | Ultralytics YOLO (`yolov8n-face.pt`) | InsightFace `buffalo_l` (ArcFace 512-d, ONNX Runtime CPU) | own ByteTrack-style tracker (NumPy) | SQLite (`sqlite3`) | stdlib `logging` | pytest.

## 6. Prerequisites

- Python 3.11, 3.12, or 3.13 (tested and verified with Python 3.13.2 on Windows 64-bit).
- A YOLO **face** model file placed at `models/yolov8n-face.pt` (~6.1 MB) - see below.
- Internet on first run (InsightFace automatically downloads `buffalo_l`, about 281 MB, to `~/.insightface/models/buffalo_l`).
- CPU-only execution verified (uses `CPUExecutionProvider`). Optional NVIDIA GPU + CUDA can be enabled if `onnxruntime-gpu` is installed.

## 7. Installation

```bash
cd katomaran-face-tracker
python -m venv .venv
# Windows:  .venv\Scripts\activate        Linux/macOS:  source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt           # runtime (ultralytics, onnxruntime, insightface, opencv-python, numpy)
pip install -r requirements-dev.txt       # + pytest
```

### Download the YOLO face model

Why this model: generic YOLO weights detect "person", not faces, so a face-trained model is required. `yolov8n-face.pt` (YOLOv8-nano trained on WIDER FACE, from <https://github.com/akanametov/yolo-face>) loads with stock Ultralytics, is small (~6.1 MB), and provides bounding boxes.
- Direct download link (Release 1.0.0):
  `curl -L -o models/yolov8n-face.pt https://github.com/akanametov/yolo-face/releases/download/1.0.0/yolov8n-face.pt`
- **Licensing:** Ultralytics is AGPL-3.0 and the face-model repo is GPL-3.0; fine for hackathon prototype evaluation, verify before commercial use. Place the model file at `models/yolov8n-face.pt` (matches `config.json`). Verified in the test environment.

## 8. Configuration (`config.json`)

| Key | Default | Meaning |
|---|---|---|
| `input.source` / `source_type` | `sample_video.mp4` / `video` | file path, or `rtsp` with `env:RTSP_URL` |
| `detection.model` | `models/yolov8n-face.pt` | YOLO face weights |
| `detection.confidence_threshold` | `0.5` | "high" confidence: starts tracks, used for recognition |
| `detection.skip_frames` | `4` | frames skipped between YOLO runs (4 = YOLO on every 5th frame; 0 = every frame) |
| `detection.device` | `auto` | `auto`, `cpu`, `cuda`, `0` |
| `recognition.similarity_threshold` | `0.45` | cosine similarity needed to call two embeddings the same person. **Starting value only - calibrate** |
| `recognition.embeddings_per_decision` | `3` | good embeddings averaged before deciding identity |
| `recognition.max_resolve_attempts` | `12` | detection cycles a track may try before it stays `UNKNOWN` |
| `quality.*` | see file | min face size, blur threshold, min confidence, edge rejection |
| `tracking.max_missing_seconds` | `2.0` | absence before EXIT (seconds, not frames) |
| `tracking.track_buffer_seconds` | `2.0` | how long a lost track is kept before removal |
| `database.path` | `data/faces.db` | SQLite file |
| `logging.file` / `level` | `logs/events.log` / `INFO` | event log |
| `storage.root` | `logs` | image root (`entries/`, `exits/`, `registrations/`) |
| `counting.scope` | `all_time` | `all_time` (database) or `session` (this run only) |

Relative paths are resolved against the folder containing `config.json`. Invalid values stop the program at start-up with a clear message.

**The defaults are not claimed to be optimal.** Tune `skip_frames`, `confidence_threshold`, quality thresholds and especially `similarity_threshold` on your video ([docs/PERFORMANCE.md](docs/PERFORMANCE.md)).

## 9. Run with an MP4 file

```bash
python -m app.main --config config.json --source path/to/sample_video.mp4
python -m app.main --source path/to/sample_video.mp4 --no-display      # headless
python -m app.main --source sample.mp4 --db data/test_run.db           # fresh database = fresh count
```
Press `q` or `ESC` in the window, or `Ctrl+C`, to stop gracefully (people still present get `EXIT reason=shutdown`).

## 10. Run with RTSP

```bash
cp .env.example .env          # then edit RTSP_URL (the .env file is git-ignored)
python -m app.main --rtsp-env RTSP_URL
```
or set `"input": {"source": "env:RTSP_URL", "source_type": "rtsp"}` in `config.json`. Never put credentials in `config.json` or source code. RTSP behaviour with a real camera is **NOT VERIFIED** (only a fake capture was tested).

## 11. Database

SQLite file `data/faces.db`: `faces` (`face_id`, `registered_at`, `embedding`, `representative_image_path`), `events` (`event_id`, `face_id`, `event_type`, `timestamp`, `source_timestamp`, `image_path`, `track_id`, `reason`), `meta`. Schema and rationale: [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md). Inspect with:

```bash
sqlite3 data/faces.db "SELECT face_id, registered_at FROM faces;"
sqlite3 data/faces.db "SELECT event_id, face_id, event_type, reason, timestamp FROM events;"
sqlite3 data/faces.db "SELECT COUNT(*) FROM faces;"     -- unique visitor count (all_time)
```

## 12. Folder structure

```
katomaran-face-tracker/
  app/
    main.py  config.py  pipeline.py  app_factory.py  models.py  errors.py  metrics.py  display.py
    input/video_source.py              # FileVideoSource, RTSPVideoSource
    detection/yolo_detector.py         # YOLO face detection
    tracking/tracker.py                # ByteTracker (Track IDs)
    recognition/                       # quality.py, face_recognizer.py (InsightFace),
                                       # identity_resolver.py, face_matcher.py, calibration.py
    registration/face_registry.py      # identify-or-register
    presence/                          # presence_manager.py, event_recorder.py, visitor_counter.py
    database/sqlite_repository.py      # all SQL lives here
    storage/image_store.py             # image paths + atomic writes
    event_logging/event_logger.py      # events.log
  tests/  docs/  scripts/calibrate_threshold.py
  data/ (faces.db)   logs/ (events.log, entries/, exits/, registrations/)   models/
  config.json  requirements.txt  .env.example  .gitignore
```

## 13. Logging

`logs/events.log`, one searchable line per event, e.g. `... | INFO | ENTRY | face_id=F001 track_id=1 image=entries/... video_time=00:00:00.200`. Events: `APPLICATION_START/STOP`, `FACE_DETECTED`, `TRACK_CREATED`, `TRACK_LOST`, `EMBEDDING_GENERATED`, `FACE_REGISTERED`, `FACE_RECOGNIZED`, `ENTRY`, `EXIT`, `DATABASE_ERROR`, `RTSP_ERROR`, `IMAGE_ERROR`. Embeddings are never logged and nothing is logged per frame.

## 14. Image storage

```
logs/entries/YYYY-MM-DD/F001_20261003T103015_120.jpg
logs/exits/YYYY-MM-DD/F001_....jpg
logs/registrations/YYYY-MM-DD/F001.jpg
```
The database stores the relative path only. Face IDs are validated before they are used in file names. Face data is local-only and git-ignored.

## 15. Testing

```bash
python -m pytest -q
```
93 tests, all passing in the build environment. See [docs/TESTING.md](docs/TESTING.md) (includes the integration checklist for real video/camera).

## 16. Performance

Measured CPU performance on 4K video: approximately **16.9 FPS** (average YOLO detection latency: ~65 ms with `skip_frames=4`). Each run prints measured per-stage timings (`detect`, `read`, `recognise`, `presence_expire`). See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for the CPU/GPU workload analysis and tuning guide.

## 17. Limitations

- Own ByteTrack-**style** tracker (simplified motion model, greedy matching); IDs can switch after long occlusion or when people cross.
- A resolved track keeps its Face ID; there is no periodic re-verification, so a track that jumps to another person would keep the old identity.
- ENTRY appears after `embeddings_per_decision` good detections (about 3 detection cycles), not on the very first frame.
- One embedding per registered face (no multi-embedding gallery); no anti-spoofing (a photo of a face counts).
- Presence-based ENTRY/EXIT (visible / not visible), not door-line crossing.
- Single process, single camera, brute-force NumPy matching (fine for hundreds of faces).

## 18. Assumptions

See [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) (counting scope, timestamps, ENTRY/EXIT meaning, and more).

## 19. Troubleshooting

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## 20. Demo instructions

1. `python -m app.main --source sample_video.mp4 --db data/demo.db`
2. Watch the window (green box = identified, orange = `UNKNOWN`, HUD shows unique visitors and FPS).
3. Show `logs/events.log`, the image folders, and the SQLite queries from section 11.
4. For the live demo: set `.env` and run `python -m app.main --rtsp-env RTSP_URL --db data/live.db`.

## 21. Demo video

> **TODO:** add your Loom / YouTube link here: `https://...`

## 22. Requirement traceability

[docs/REQUIREMENTS_MATRIX.md](docs/REQUIREMENTS_MATRIX.md) maps every requirement to code and an honest verification status.

---

This project is a part of a hackathon run by https://katomaran.com
