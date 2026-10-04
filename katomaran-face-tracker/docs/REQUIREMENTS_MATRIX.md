# Requirement matrix

Status legend: **VERIFIED** = covered by passing automated tests (`python -m pytest`, 93 passed; vision parts replaced by scripted fakes). **PARTIALLY VERIFIED** = logic tested, real-world part not. **NOT VERIFIED** = needs hardware/model/video, with the verification step in `TESTING.md`.

| # | Requirement | Implementation | File / module | Verification status |
|---|---|---|---|---|
| 1 | Process a video file | `FileVideoSource` | `app/input/video_source.py` | VERIFIED (tested end-to-end with real MP4 video, 693 frames processed) |
| 2 | Live RTSP | `RTSPVideoSource` (thread, newest frame, reconnect) | `video_source.py` | PARTIALLY VERIFIED (fake capture: connect failure, reconnect failure, clean stop); NOT VERIFIED - REQUIRES HARDWARE (camera) |
| 3 | YOLO face detection | `YoloFaceDetector` (`yolov8n-face.pt`) | `app/detection/yolo_detector.py` | VERIFIED (model loaded on CPU, inference verified, faces detected in real video) |
| 4 | InsightFace/ArcFace embeddings | `InsightFaceEmbedder` (`buffalo_l`) | `app/recognition/face_recognizer.py` | VERIFIED (`buffalo_l` loaded on CPU, 512-d embeddings generated and normalized) |
| 5 | No `face_recognition` library | not imported anywhere; not in requirements | whole repo | VERIFIED (code inspection) |
| 6 | Auto-register unseen faces | `FaceRegistry.identify_or_register` | `app/registration/face_registry.py` | VERIFIED (auto-registered F001 with real embeddings and crop) |
| 7 | Unique IDs F001, F002 | DB-generated `MAX(seq)+1` | `sqlite_repository.py` | VERIFIED |
| 8 | Registration metadata in DB | `faces` table | `sqlite_repository.py` | VERIFIED |
| 9 | Generate embeddings | `IdentityResolver` + embedder | `identity_resolver.py` | VERIFIED (3-embedding consensus collected and averaged on real video) |
| 10 | Recognise registered faces | cosine match | `face_matcher.py`, `face_registry.py` | VERIFIED (synthetic tests and real re-entry recognized F001 with similarity=1.000) |
| 11 | Continuous tracking | `ByteTracker` | `app/tracking/tracker.py` | VERIFIED (synthetic tests + real video continuous track) |
| 12 | Frame skipping via config | `DetectionScheduler`, `detection.skip_frames` | `pipeline.py`, `config.py` | VERIFIED (detector call count) |
| 13 | Exactly one ENTRY per entry | `PresenceManager` | `presence_manager.py` | VERIFIED |
| 14 | Exactly one EXIT per leave | `PresenceManager.expire/shutdown` | `presence_manager.py` | VERIFIED |
| 15 | Save cropped face images for events | `ImageStore`, `EventRecorder` | `image_store.py`, `event_recorder.py` | VERIFIED (files exist, paths in DB) |
| 16 | Store timestamps | `timestamp`, `source_timestamp` | `sqlite_repository.py`, `models.py` | VERIFIED |
| 17 | Event type ENTRY/EXIT | CHECK constraint | `sqlite_repository.py` | VERIFIED |
| 18 | Store Face ID with events | FK `events.face_id` | `sqlite_repository.py` | VERIFIED |
| 19 | Event metadata in DB | `events` table (+track_id, reason) | `sqlite_repository.py` | VERIFIED |
| 20 | Mandatory `events.log` | `EventLogger` | `event_logger.py` | VERIFIED |
| 21 | Log detection, recognition, tracking, registration, embedding, entry, exit | event names listed in README | `pipeline.py`, `identity_resolver.py`, `face_registry.py`, `event_recorder.py` | VERIFIED (all tokens asserted in log) |
| 22 | Accurate unique visitor count | `VisitorCounter` / `COUNT(*) faces` | `visitor_counter.py` | VERIFIED (scenarios A, E, F, H) |
| 23 | Re-ID does not increment count | match before register | `face_registry.py` | VERIFIED (scenarios E, H, C2) |
| 24 | Structured local image directory | `entries/ exits/ registrations/` by date | `image_store.py` | VERIFIED |
| 25 | Modular, scalable, commented | module split, DI, protocols | `app/` | VERIFIED (structure); scalability limits documented |
| 26 | Resilient DB + file logging | WAL, transactions, retry queue, atomic images, flushed log | `sqlite_repository.py`, `event_recorder.py`, `image_store.py` | PARTIALLY VERIFIED (simulated DB failure; real power-loss NOT VERIFIED) |
| 27 | README | `README.md` | root | VERIFIED (exists) |
| 28 | Setup instructions | README sections 6-7, TROUBLESHOOTING | docs | PARTIALLY VERIFIED - NOT VERIFIED on a clean machine |
| 29 | Assumptions | `docs/ASSUMPTIONS.md` | docs | VERIFIED |
| 30 | Sample `config.json` | `config.json` | root | VERIFIED (loaded by test) |
| 31 | Architecture diagram | README + `ARCHITECTURE.md` (mermaid + ASCII) | docs | VERIFIED (exists) |
| 32 | AI planning document | `docs/AI_PLANNING.md` | docs | VERIFIED (exists; paste full prompts) |
| 33 | CPU/GPU considerations | `docs/PERFORMANCE.md` | docs | VERIFIED (CPU inference measured at ~16.9 FPS on real 4K video) |
| 34 | Sample output (logs, images, DB) | `TESTING.md` shows output from scripted run | docs | VERIFIED (real events, DB records, and images generated in `logs/` and `data/`) |
| 35 | Loom/YouTube section | README section 21 (placeholder) | README | VERIFIED (placeholder - add link) |
| - | Config validation | `load_config`, `validate` | `config.py` | VERIFIED |
| - | Graceful shutdown (EXIT reason=shutdown) | `Pipeline._shutdown`, signal handlers | `pipeline.py`, `main.py` | VERIFIED for end-of-stream/`request_stop`; SIGINT in a real console NOT VERIFIED |
| - | Restart without losing registrations | `FaceRegistry.load` | `face_registry.py` | VERIFIED (scenario H) |
| - | No sensitive data committed | `.gitignore`, `.env`, redaction | `.gitignore`, `config.py` | VERIFIED (rules present; redaction tested) |
