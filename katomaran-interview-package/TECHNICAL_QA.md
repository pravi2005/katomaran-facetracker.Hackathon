# Technical Q&A
Format per item: QUESTION / SHORT INTERVIEW ANSWER / DETAILED EXPLANATION / WHERE IT APPEARS IN OUR CODE / POSSIBLE FOLLOW-UP / FOLLOW-UP ANSWER.

## 1. What is the difference between a detection, a Track ID and a Face ID?

**QUESTION:** What is the difference between a detection, a Track ID and a Face ID?

**SHORT INTERVIEW ANSWER:** Detection = where a face is in one frame; Track ID = the tracker's temporary label for the same box over time; Face ID = the permanent identity (F001) decided by embedding match.

**DETAILED EXPLANATION:** A detection has no memory. The tracker adds continuity but can change IDs after occlusion. Recognition adds identity. Presence (ENTRY/EXIT) is keyed by Face ID so a Track ID change cannot cause a duplicate ENTRY.

**WHERE IT APPEARS IN OUR CODE:** `app/models.py` (Detection, Track), `app/recognition/identity_resolver.py` (Track ID -> Face ID), `app/presence/presence_manager.py` (keyed by face_id).

**POSSIBLE FOLLOW-UP:** What proves a Track ID changed but Face ID did not?

**FOLLOW-UP ANSWER:** `test_c2_track_id_switch_does_not_duplicate_entry` and the sample log: `ENTRY face_id=F001 track_id=1` then later `ENTRY face_id=F001 track_id=3`.

## 2. Why did you use YOLO and which model?

**QUESTION:** Why did you use YOLO and which model?

**SHORT INTERVIEW ANSWER:** The brief requires YOLO; I use a face-trained nano model (`yolov8n-face.pt`) loaded with Ultralytics because generic YOLO weights detect persons, not faces.

**DETAILED EXPLANATION:** Nano = fast. It's trained on WIDER FACE and is box-only (no landmarks). Licences: Ultralytics AGPL-3.0, model repo GPL-3.0. The path is configurable in `detection.model`; the file is not bundled and was not run in the build environment.

**WHERE IT APPEARS IN OUR CODE:** `app/detection/yolo_detector.py`, `config.json` -> `detection`.

**POSSIBLE FOLLOW-UP:** How do you get face alignment without landmarks?

**FOLLOW-UP ANSWER:** InsightFace's own detector runs on a padded crop to give 5 landmarks (`_embed_via_insightface_detector`); only for unresolved tracks. A YOLO model with keypoints would use `norm_crop` directly.

## 3. How does frame skipping work and what is the trade-off?

**QUESTION:** How does frame skipping work and what is the trade-off?

**SHORT INTERVIEW ANSWER:** YOLO runs every `skip_frames+1` frames; the tracker predicts box movement in between.

**DETAILED EXPLANATION:** `DetectionScheduler.should_detect()` returns true when `count % (skip_frames+1) == 0`. Less detection saves compute but boxes drift and brief appearances can be missed; more detection is more robust but costs more. Keep `(skip_frames+1)/fps < max_missing_seconds` (a `CONFIG_WARNING` is logged otherwise).

**WHERE IT APPEARS IN OUR CODE:** `app/pipeline.py` (`DetectionScheduler`, `_warn_if_timeout_too_short`), `ByteTracker.predict`.

**POSSIBLE FOLLOW-UP:** Is a coasting prediction used as proof the person is present?

**FOLLOW-UP ANSWER:** No. Only tracks matched to a fresh detection (`matched_this_update`) feed identity and presence.

## 4. Explain how your tracker works. Is it really ByteTrack?

**QUESTION:** Explain how your tracker works. Is it really ByteTrack?

**SHORT INTERVIEW ANSWER:** It's ByteTrack-style: two-stage association (high-confidence, then low-confidence for leftover tracks) with a simplified motion model.

**DETAILED EXPLANATION:** Differences from the reference: damped constant-velocity instead of Kalman; greedy IoU matching instead of Hungarian. The interface (`predict`, `update`) is small so Ultralytics' BYTETracker can replace it.

**WHERE IT APPEARS IN OUR CODE:** `app/tracking/tracker.py`, `tests/test_tracker.py`.

**POSSIBLE FOLLOW-UP:** Why not just use the Ultralytics tracker?

**FOLLOW-UP ANSWER:** To avoid an extra coupling to a changing API, keep it testable without models, and handle skipped frames explicitly; trade-off is a simpler tracker.

## 5. How do you decide whether a face is new or already registered?

**QUESTION:** How do you decide whether a face is new or already registered?

**SHORT INTERVIEW ANSWER:** Average three good normalised embeddings, compute cosine similarity to every stored face, and compare the best score to `recognition.similarity_threshold`.

**DETAILED EXPLANATION:** At or above the threshold -> existing Face ID, nothing written. Below -> the database creates the next Face ID, the embedding/image/metadata are stored and the gallery updated immediately.

**WHERE IT APPEARS IN OUR CODE:** `IdentityResolver._decide`, `FaceRegistry.identify_or_register`, `FaceMatcher.best_match`.

**POSSIBLE FOLLOW-UP:** What if the gallery is empty?

**FOLLOW-UP ANSWER:** `best_match` returns `(None, -1.0)`, so the first good face is registered as F001.

## 6. What is cosine similarity and why normalise embeddings?

**QUESTION:** What is cosine similarity and why normalise embeddings?

**SHORT INTERVIEW ANSWER:** It measures the angle between two vectors (-1..1, higher = more alike); after L2-normalising, it equals the dot product.

**DETAILED EXPLANATION:** ArcFace is trained so identity is expressed by angle. `normalize()` rejects NaN, infinite and zero vectors.

**WHERE IT APPEARS IN OUR CODE:** `app/recognition/face_matcher.py`.

**POSSIBLE FOLLOW-UP:** Why a matrix product rather than a loop?

**FOLLOW-UP ANSWER:** One `matrix @ vector` compares against all faces at once; exact and fast for thousands of faces.

## 7. How did you choose the threshold 0.45?

**QUESTION:** How did you choose the threshold 0.45?

**SHORT INTERVIEW ANSWER:** It's a starting value in a commonly used range, not claimed optimal; it must be calibrated on the real video.

**DETAILED EXPLANATION:** Calibration compares same-person vs different-person similarities: pick a value between the 5th percentile of same-person and the 95th percentile of different-person scores; if they overlap, improve crops. Too low = false matches; too high = duplicate IDs.

**WHERE IT APPEARS IN OUR CODE:** `scripts/calibrate_threshold.py`, `app/recognition/calibration.py` (unit-tested), `config.json`.

**POSSIBLE FOLLOW-UP:** What threshold did you finally use?

**FOLLOW-UP ANSWER:** Answer with your own measured value and evidence (not verified by the build).

## 8. How do you guarantee exactly one ENTRY and one EXIT per visit?

**QUESTION:** How do you guarantee exactly one ENTRY and one EXIT per visit?

**SHORT INTERVIEW ANSWER:** A state machine per Face ID: ENTRY only on ABSENT->PRESENT, EXIT only when a MISSING session passes the timeout or at shutdown, and the session is removed on EXIT.

**DETAILED EXPLANATION:** States: ABSENT, PRESENT, MISSING. Absence shorter than `max_missing_seconds` never emits anything.

**WHERE IT APPEARS IN OUR CODE:** `app/presence/presence_manager.py`, tests A-H.

**POSSIBLE FOLLOW-UP:** What if a person disappears for 1.5 s with a 2 s timeout?

**FOLLOW-UP ANSWER:** State goes MISSING, no event; when they return it silently goes back to PRESENT (even with a new Track ID).

## 9. Why seconds and not frames for the timeout?

**QUESTION:** Why seconds and not frames for the timeout?

**SHORT INTERVIEW ANSWER:** Frame counts mean different durations at different FPS; seconds on the stream clock behave the same for files and RTSP.

**DETAILED EXPLANATION:** File sources use video time (`index/fps`), RTSP uses wall time, via `FrameTime.stream_seconds`.

**WHERE IT APPEARS IN OUR CODE:** `app/models.py` (FrameTime), `app/input/video_source.py`.

**POSSIBLE FOLLOW-UP:** Why video time for files?

**FOLLOW-UP ANSWER:** Results don't change if you process faster or slower than real time; wall time is stored separately.

## 10. How is the unique visitor count defined and computed?

**QUESTION:** How is the unique visitor count defined and computed?

**SHORT INTERVIEW ANSWER:** Distinct Face IDs; default scope `all_time` = `SELECT COUNT(*) FROM faces`.

**DETAILED EXPLANATION:** Re-identification never inserts into `faces`, so returns don't increment. `counting.scope=session` counts only IDs seen in this run.

**WHERE IT APPEARS IN OUR CODE:** `app/presence/visitor_counter.py`, `SQLiteRepository.count_faces`.

**POSSIBLE FOLLOW-UP:** How do you reset the count for a demo?

**FOLLOW-UP ANSWER:** Run with a fresh database: `--db data/new.db`.

## 11. How is the database designed?

**QUESTION:** How is the database designed?

**SHORT INTERVIEW ANSWER:** Three tables: `faces`, `events`, `meta`; images are files, paths are stored.

**DETAILED EXPLANATION:** IDs generated in a `BEGIN IMMEDIATE` transaction using `MAX(seq)+1`; CHECK and FK constraints; WAL mode; embeddings as float32 BLOB; model/dimension recorded in `meta`.

**WHERE IT APPEARS IN OUR CODE:** `app/database/sqlite_repository.py`, `docs/DATABASE_DESIGN.md`.

**POSSIBLE FOLLOW-UP:** What if a different model is used later?

**FOLLOW-UP ANSWER:** `ensure_embedding_compatibility` raises `IncompatibleEmbeddingError`; use a new database.

## 12. How do you make logging and storage resilient?

**QUESTION:** How do you make logging and storage resilient?

**SHORT INTERVIEW ANSWER:** Flushed log lines, atomic image writes, transactions, and a retry queue for failed event inserts.

**DETAILED EXPLANATION:** An image failure still records the event (NULL path); a DB failure queues the row and logs `DATABASE_ERROR`; queue flushes on the next event and at shutdown.

**WHERE IT APPEARS IN OUR CODE:** `app/presence/event_recorder.py`, `app/storage/image_store.py`, `app/event_logging/event_logger.py`, `tests/test_event_recorder.py`.

**POSSIBLE FOLLOW-UP:** What can still be lost?

**FOLLOW-UP ANSWER:** Queued events if the process dies while the DB is still failing (queue is in memory, max 1000).

## 13. How does RTSP input work and how is it made robust?

**QUESTION:** How does RTSP input work and how is it made robust?

**SHORT INTERVIEW ANSWER:** A reader thread keeps only the newest frame; on disconnect it reconnects up to a limit, then raises a clear error.

**DETAILED EXPLANATION:** Prevents buffer lag; credentials come from `.env` via `env:RTSP_URL` and are redacted in logs/errors.

**WHERE IT APPEARS IN OUR CODE:** `RTSPVideoSource` in `app/input/video_source.py`, `config.redact_url`.

**POSSIBLE FOLLOW-UP:** Was it tested with a camera?

**FOLLOW-UP ANSWER:** Only with a fake capture in tests; the real camera test is on the checklist (say what you observed).

## 14. How do you avoid computing embeddings repeatedly?

**QUESTION:** How do you avoid computing embeddings repeatedly?

**SHORT INTERVIEW ANSWER:** Per-track state: once a Track has a Face ID, `resolve()` returns it immediately.

**DETAILED EXPLANATION:** Unresolved tracks gather 3 good embeddings then decide; a test asserts the embedder was called exactly twice for a stable track with 2 embeddings required.

**WHERE IT APPEARS IN OUR CODE:** `IdentityResolver.resolve`, `test_b_person_stays_visible_no_duplicates`.

**POSSIBLE FOLLOW-UP:** What's the downside?

**FOLLOW-UP ANSWER:** Identity isn't re-verified; a track that jumps to another person keeps the old identity.

## 15. What does the quality gate do and why?

**QUESTION:** What does the quality gate do and why?

**SHORT INTERVIEW ANSWER:** Rejects low-confidence, tiny, blurry or frame-edge faces before embedding.

**DETAILED EXPLANATION:** Bad crops produce noisy embeddings, the main cause of duplicate IDs. Blur = variance of the Laplacian on a 112x112 grayscale resize.

**WHERE IT APPEARS IN OUR CODE:** `app/recognition/quality.py`.

**POSSIBLE FOLLOW-UP:** Why fixed-size resize before measuring blur?

**FOLLOW-UP ANSWER:** Sharpness scores then compare fairly across face sizes.

## 16. How is configuration validated?

**QUESTION:** How is configuration validated?

**SHORT INTERVIEW ANSWER:** `load_config` builds dataclasses, rejects unknown keys/wrong types, and `validate` checks ranges, raising `ConfigError` at start-up.

**DETAILED EXPLANATION:** Relative paths resolve against the config file; secrets via `env:` names.

**WHERE IT APPEARS IN OUR CODE:** `app/config.py`, `tests/test_config.py`.

**POSSIBLE FOLLOW-UP:** Why reject unknown keys?

**FOLLOW-UP ANSWER:** A typo like `skipframes` would otherwise silently use the default.

## 17. How is the application tested without a camera or GPU?

**QUESTION:** How is the application tested without a camera or GPU?

**SHORT INTERVIEW ANSWER:** Dependency injection: fake source, detector and embedder drive the real pipeline, tracker, registry, DB and logger.

**DETAILED EXPLANATION:** 93 tests cover scenarios A-H, presence, DB, config, logging, video source (synthetic video, fake RTSP capture), tracker.

**WHERE IT APPEARS IN OUR CODE:** `tests/helpers.py`, `tests/test_pipeline_scenarios.py`.

**POSSIBLE FOLLOW-UP:** What isn't tested?

**FOLLOW-UP ANSWER:** Real model accuracy, GPU path, real RTSP network, OpenCV window, SIGINT in a console.

## 18. How would you scale this to many cameras and many people?

**QUESTION:** How would you scale this to many cameras and many people?

**SHORT INTERVIEW ANSWER:** One worker per camera, PostgreSQL instead of SQLite, a vector index (FAISS) for matching, camera ID on events, message queue for storage.

**DETAILED EXPLANATION:** Current design is single-process; matching is brute force; SQLite serialises writes.

**WHERE IT APPEARS IN OUR CODE:** `docs/PERFORMANCE.md`.

**POSSIBLE FOLLOW-UP:** What changes in recognition for multiple cameras?

**FOLLOW-UP ANSWER:** Thresholds need per-camera calibration; consider storing several embeddings per person.

## 19. How did you handle privacy and security?

**QUESTION:** How did you handle privacy and security?

**SHORT INTERVIEW ANSWER:** Face data local only, git-ignored; embeddings never logged; RTSP credentials in `.env` and redacted; Face IDs validated before building file paths.

**DETAILED EXPLANATION:** `.gitignore` excludes DB, logs, images, models, videos, `.env`. In production you'd add consent, retention limits and encryption.

**WHERE IT APPEARS IN OUR CODE:** `.gitignore`, `config.redact_url`, `ImageStore`, `EventLogger._format_value`.

**POSSIBLE FOLLOW-UP:** Could a crafted Face ID write outside the folder?

**FOLLOW-UP ANSWER:** No: IDs must match `^F\d{3,}$` before use in a path (`test_unsafe_face_ids_rejected`).

## 20. What did the AI do and what did you do?

**QUESTION:** What did the AI do and what did you do?

**SHORT INTERVIEW ANSWER:** AI generated plans and code under my requirements; I reviewed architecture, decided the key rules, and I own testing, calibration and explanation.

**DETAILED EXPLANATION:** Be specific and honest about what you personally ran and verified.

**WHERE IT APPEARS IN OUR CODE:** `docs/AI_PLANNING.md`, `AI_PROMPTS.md`.

**POSSIBLE FOLLOW-UP:** Show me something you changed.

**FOLLOW-UP ANSWER:** Be ready to change a config/timeout or add a column live.
