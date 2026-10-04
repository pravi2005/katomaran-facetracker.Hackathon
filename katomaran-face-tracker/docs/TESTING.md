# Testing

```bash
python -m pytest -q          # 93 tests; all passed in the build environment (Python 3.12, no GPU, no models)
```

## What is automated (and how)

The real YOLO, InsightFace, video and camera are replaced by scripted fakes in `tests/helpers.py` (fake detector, fake embedder with per-person vectors + noise, scripted video). Everything else in the scenario tests is the **real** code: tracker, resolver, registry, presence manager, recorder, SQLite, image store, logger.

| File | Tests | Covers |
|---|---|---|
| `test_pipeline_scenarios.py` | 11 | Spec scenarios A-H end to end, images + log content, frame skipping |
| `test_presence_manager.py` | 8 | first appearance, continued presence, temporary loss, timeout, re-entry, shutdown, dedupe |
| `test_matcher_registry.py` | 7 | new face, duplicate face, different person, threshold, restart persistence, bad vectors |
| `test_repository.py` | 8 | insert/retrieve face + events, constraints, persistence, embedding serialization, compatibility check |
| `test_config.py` | 18 | valid / missing / invalid JSON / out-of-range / unknown keys / `env:` source / `.env` / credential redaction |
| `test_event_logger.py` | 5 | file creation, line format, embeddings never logged, level, flush |
| `test_event_recorder.py` | 3 | image + row + log, DB-failure retry queue, image failure |
| `test_image_store.py` | 11 | directory layout, unsafe IDs, no overwrite, crop padding |
| `test_tracker.py` | 9 | IDs, coasting, buffer removal, low-confidence stage, ID never reused |
| `test_video_source.py` | 8 | missing/corrupt file, read to EOF, timestamps, close; RTSP with fake capture (connect failure, reconnect failure, clean stop, no credentials in logs) |
| `test_quality.py` / `test_calibration.py` | 2 / 3 | quality gate, threshold calibration maths |

### Spec scenario mapping

| Scenario | Test |
|---|---|
| A new person enters (F001, ENTRY, count 1) | `test_a_new_person_enters` |
| B stays visible (no duplicate registration/ENTRY) | `test_b_person_stays_visible_no_duplicates` |
| C temporary disappearance (no EXIT) | `test_c_temporary_disappearance_no_exit`, `test_c2_track_id_switch_...` |
| D genuinely leaves (exactly one EXIT) | `test_d_person_leaves_exactly_one_exit` |
| E returns (F001, count unchanged, new ENTRY) | `test_e_reentry_same_face_id_count_unchanged` |
| F second person (F002, count 2) | `test_f_second_person_gets_f002` |
| G two simultaneous people | `test_g_two_people_simultaneously` |
| H DB persists across restart | `test_h_database_persists_across_restart` |

## Sample output - from the automated scenario run (SCRIPTED FAKES, not real video)

This is real output produced by running the pipeline with the scripted fake detector/embedder (person A visible, B appears, A returns). It proves the logging/DB format, **not** model accuracy. Timestamps of the video are simulated.

```
FACE_DETECTED | track_id=1 confidence=0.950
TRACK_CREATED | track_id=1
EMBEDDING_GENERATED | track_id=1 dim=64 collected=1
EMBEDDING_GENERATED | track_id=1 dim=64 collected=2
FACE_REGISTERED | face_id=F001 track_id=1 image=registrations/2026-10-03/F001.jpg
ENTRY | face_id=F001 track_id=1 image=entries/2026-10-03/F001_20261003T100000_200.jpg video_time=00:00:00.200
TRACK_LOST | track_id=1 face_id=F001
...
FACE_REGISTERED | face_id=F002 track_id=2 closest_existing_similarity=-0.028 ...
ENTRY | face_id=F002 track_id=2 ... video_time=00:00:03.200
EXIT | face_id=F001 track_id=1 ... reason=person_left absent_seconds=2.100 video_time=00:00:03.900
FACE_RECOGNIZED | face_id=F001 track_id=3 similarity=0.997
ENTRY | face_id=F001 track_id=3 ... video_time=00:00:06.200
EXIT | face_id=F002 track_id=2 ... reason=person_left absent_seconds=2.100
EXIT | face_id=F001 track_id=3 ... reason=shutdown
```
```
event_id face_id event_type reason       source_timestamp track_id
1        F001    ENTRY      NULL         00:00:00.200     1
2        F002    ENTRY      NULL         00:00:03.200     2
3        F001    EXIT       person_left  00:00:03.900     1
4        F001    ENTRY      NULL         00:00:06.200     3     <- same Face ID, new Track ID, new session
5        F002    EXIT       person_left  00:00:06.900     2
6        F001    EXIT       shutdown     00:00:08.900     3
faces: F001, F002   COUNT(*) = 2
```
Real sample output from the real models (images, logs, database rows) must be captured by you: **NOT VERIFIED - REQUIRES SAMPLE VIDEO**.

## Integration checklist (REQUIRES real model / video / camera)

Run these on your machine and record the results yourself:

1. **Models load:** `python -m app.main --source sample.mp4 --no-display --max-frames 50`. Expect `MODELS_READY` in the log with the device and `embedding_dim`. Failure modes are explained in TROUBLESHOOTING.
2. **YOLO sanity:** run with the display on; boxes should sit on faces. Judge by eye; adjust `detection.confidence_threshold` / `detection.image_size`.
3. **Tracking:** with 2+ people, each should keep its own Track ID while visible.
4. **Recognition:** the same person re-entering must show the same `F###`. If one person gets two IDs -> raise recall (lower threshold slightly / better quality gate); if two people share an ID -> raise the threshold. Use `scripts/calibrate_threshold.py` with crops from `logs/entries/` sorted by person.
5. **ENTRY/EXIT:** walk out of view for less than 2 s (no EXIT) and for more than 2 s (EXIT, `person_left`).
6. **Unique count:** compare the HUD / `SELECT COUNT(*) FROM faces` with the real number of people in the video (use a fresh `--db`).
7. **Restart:** run twice with the same `--db`; known faces must keep their IDs (`known_faces=N` in `MODELS_READY`).
8. **Shutdown:** press `q` while someone is visible; expect `EXIT ... reason=shutdown`.
9. **RTSP:** run against the camera; unplug the network briefly; expect `RTSP_ERROR` lines then `reconnected`, or a clean error after the retry limit.
10. **Timing:** note the printed `--- run metrics (measured) ---` block per stage on your hardware.

## Not covered by automated tests

Real model accuracy, GPU path, real RTSP network behaviour, OpenCV window display, signal handling (SIGINT) in a real console, very long runs.
