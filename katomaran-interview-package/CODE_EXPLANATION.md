# Code explanation (module by module)

Paths are relative to `katomaran-face-tracker/`. For each module: purpose, key classes/functions, input -> output, important logic, common bugs, likely questions.

## `app/main.py`
- **Purpose:** CLI entry. `parse_args`, `main`.
- **Flow:** load config -> apply overrides (`--source`, `--rtsp-env`, `--db`, `--no-display`) -> `build_app` -> install SIGINT/SIGTERM handlers that call `pipeline.request_stop()` -> `with pipeline.source:` run -> log `APPLICATION_STOP`, print measured metrics -> always `app.close()`.
- **Exit codes:** 2 = start-up error (config/model/DB), 1 = runtime `AppError`, 0 = OK.
- **Common bugs:** running from the wrong folder (config path); forgetting that relative paths resolve against the config file's folder.
- **Q:** "How does graceful shutdown work?" -> signal sets a flag; the loop ends; `Pipeline._shutdown` emits EXIT `shutdown` for everyone present and flushes pending DB events.

## `app/config.py`
- **Purpose:** typed config dataclasses + validation. `load_config`, `validate`, `resolve_source`, `redact_url`, `load_dotenv`.
- **Logic:** `_build` rejects unknown keys and wrong types (ints accepted for floats); `validate` range-checks (e.g. thresholds, `skip_frames >= 0`, `max_resolve_attempts >= embeddings_per_decision`); `env:NAME` sources read secrets from the environment or git-ignored `.env`.
- **Common bugs:** typos in keys (now an error, not silently ignored).
- **Q:** "Why not hard-code thresholds?" -> tuning must not need code changes; values differ per camera and video.

## `app/pipeline.py`
- **Purpose:** the loop. Classes: `Pipeline`, `DetectionScheduler`, `RunSummary`.
- **Per frame:** `tracker.predict()`; if scheduler says detect: `_detection_cycle` (YOLO -> `tracker.update` -> log `FACE_DETECTED/TRACK_CREATED/TRACK_LOST` -> for tracks matched this cycle `resolver.resolve` -> `presence.update`); then `presence.expire` every frame; display.
- **Important:** only tracks with `matched_this_update` count as "seen" - a coasting prediction is not evidence that the person is there.
- **Common bugs:** detection interval longer than the absence timeout -> false EXITs (warning logged).
- **Q:** "Where is frame skipping?" -> `DetectionScheduler.should_detect`, `frame_count % (skip_frames+1) == 0`.

## `app/app_factory.py`
- Composition root. Builds source, YOLO detector, InsightFace embedder, repository (+ embedding compatibility check), image store, registry (loads gallery from DB), resolver, presence manager, recorder, counter, display. On failure it closes DB and logger.

## `app/input/video_source.py`
- **Classes:** `VideoSource` (abstract: `open/read/close/fps`), `FileVideoSource`, `RTSPVideoSource`.
- **File:** returns `Frame(image, index, FrameTime)`; `None` at end; invalid frames skipped (30 in a row -> `SourceError`); time = `index/fps`.
- **RTSP:** background thread keeps only the newest frame (so no growing lag), reconnects up to `reconnect_max_attempts`, raises `SourceError` if lost; credentials removed by `redact_url` in all logs/errors; TCP transport hint via `OPENCV_FFMPEG_CAPTURE_OPTIONS`.
- **Bugs to know:** RTSP behaviour with a real camera is unverified; stalled `cap.read()` can block the reader thread.
- **Q:** "Why a thread?" -> OpenCV buffers frames; without it you process old video.

## `app/detection/yolo_detector.py`
- **Class:** `YoloFaceDetector.detect(image) -> list[Detection]`. Lazy `ultralytics` import; `resolve_device("auto")` picks CUDA if PyTorch sees one.
- **Model:** `yolov8n-face.pt` (WIDER FACE-trained, box-only). Licences: Ultralytics AGPL-3.0, model repo GPL-3.0.
- **Logic:** runs with the *low* confidence floor so the tracker can use low-score boxes; the tracker splits high/low.
- **Q:** "Why a face-specific model?" -> generic COCO YOLO detects person, not face.

## `app/tracking/tracker.py`
- **Class:** `ByteTracker` with `predict()`, `update(detections, now) -> (new_tracks, removed_tracks)`, `drain()`; helper `iou`.
- **Logic:** stage 1 high-confidence detections vs all tracks (IoU >= 0.3); stage 2 low-confidence vs leftover tracks (IoU >= 0.5); new tracks only from unmatched high-confidence detections; tracks removed when unmatched longer than `track_buffer_seconds`; between detections, boxes move by a decaying velocity.
- **Honest differences from ByteTrack:** no Kalman filter, greedy instead of Hungarian.
- **Q:** "Why can Track ID change?" -> no appearance features; after long occlusion a new track starts. That's why identity lives in Face ID.

## `app/recognition/quality.py`
- `QualityChecker.check` rejects: low confidence, face smaller than `min_face_size_px`, box touching frame edge, blur (variance of Laplacian on a 112x112 grayscale resize). Result has a reason string.

## `app/recognition/face_recognizer.py`
- **Class:** `InsightFaceEmbedder.embed(image, bbox, landmarks) -> normalized vector | None`.
- **Logic:** with 5 landmarks -> `norm_crop` to 112x112 -> ArcFace `get_feat`; without (default) -> InsightFace's detector on a padded crop to find landmarks, then embedding. Embedding dimension measured with a dummy image. Providers: CUDA if `onnxruntime-gpu` available, else CPU.
- **Unverified:** real model run. Download on first use (~280 MB).

## `app/recognition/identity_resolver.py`
- **Class:** `IdentityResolver.resolve(track, frame) -> face_id | None`, `forget`.
- **State per Track ID:** collected embeddings, best (sharpest) crop, attempts, resolved face ID.
- **Logic:** if resolved -> return (no compute). Else quality gate -> embed -> collect; at `embeddings_per_decision` average and call `FaceRegistry.identify_or_register`; give up after `max_resolve_attempts`.
- **Bug class:** crossing people may swap tracks; identity is not re-verified (known limitation).

## `app/recognition/face_matcher.py` and `app/registration/face_registry.py`
- `normalize`, `FaceMatcher.add/best_match` (matrix product = cosine). `FaceRegistry.load` fills the gallery from the DB; `identify_or_register`: `similarity >= threshold` -> existing; else `create_face` (DB generates ID) -> add to gallery -> save image -> `FACE_REGISTERED`.
- **Q:** "What if two tracks of the same new person resolve at once?" -> the gallery is updated immediately, so the second one matches the first.

## `app/presence/presence_manager.py`
See `ENTRY_EXIT_LOGIC.md`. Pure logic, no I/O.

## `app/presence/event_recorder.py`
- `record(event)`: flush pending -> save image (failure -> NULL path) -> insert row (failure -> queue + `DATABASE_ERROR`) -> log ENTRY/EXIT line.

## `app/database/sqlite_repository.py`
See `DATABASE_EXPLANATION.md`. All SQL; `DatabaseError` wrapper; `ensure_embedding_compatibility`.

## `app/storage/image_store.py`
- Validates Face ID (`^F\d{3,}$`) before building paths (no path traversal), encodes with `cv2.imencode` and writes via temp file + atomic rename, returns relative posix path, avoids same-millisecond overwrite.

## `app/event_logging/event_logger.py`
- `EventLogger.log(event, **fields)` -> `time | LEVEL | EVENT | key=value ...`. Arrays are never printed. `FileHandler` flushes each record. Event name constants live here.
- **Q:** "Why `event_logging` and not `logging`?" -> a package named `logging` can shadow the stdlib module.

## Others
`models.py` (dataclasses: `Frame`, `FrameTime`, `Detection`, `Track`, `Observation`, `PresenceEvent`), `errors.py` (exception hierarchy), `metrics.py` (measured FPS/stage times), `display.py` (overlay), `presence/visitor_counter.py` (count scopes), `recognition/calibration.py` + `scripts/calibrate_threshold.py` (threshold calibration).
