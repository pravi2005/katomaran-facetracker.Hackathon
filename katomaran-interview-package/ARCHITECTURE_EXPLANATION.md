# Architecture explanation

```
VideoSource -> Pipeline loop
   |            |- tracker.predict()            (every frame)
   |            |- DetectionScheduler -> YOLO -> tracker.update()   (every skip_frames+1)
   |            |- IdentityResolver (quality -> embedding x3 -> average)
   |            |      `- FaceRegistry (cosine vs gallery: existing / register)
   |            |- PresenceManager.update()/expire()  -> ENTRY / EXIT
   |            `- EventRecorder -> image file + SQLite + events.log
   `- shutdown: PresenceManager.shutdown() -> EXIT(reason=shutdown)
```

## Why this shape
- **Pipeline is dumb orchestration.** It receives a detector, tracker, resolver, presence manager and recorder through the constructor (`app_factory.py` builds the real ones; tests inject fakes). This is why 93 tests run without a GPU.
- **One responsibility per module.** Detection doesn't know tracking; presence doesn't know SQL; SQL lives only in `sqlite_repository.py`.
- **Four concepts, never merged:** Detection (a box now), Track ID (tracker label, can change), Face ID (permanent identity), Presence state (per Face ID).

## Key decisions and the "why"
| Decision | Why |
|---|---|
| Presence keyed by Face ID | tracker ID switches must not produce new ENTRYs |
| Timeout in seconds on a stream clock | frames-per-second differ between file and RTSP; video time makes file runs reproducible |
| Identity decided from 3 averaged embeddings | single blurry frame must not create a new person |
| Resolved tracks are never re-embedded | main compute saving |
| DB-generated Face IDs | survive restarts, no in-memory counter |
| Embedding dimension and model name in `meta` | refuse to compare vectors from different models |
| Own tracker | no extra dependency, testable; replaceable via `predict()`/`update()` |
| Retry queue in `EventRecorder` | DB hiccup must not crash a live demo |

## Failure handling by layer
- Source: missing/corrupt file -> `SourceError`; RTSP drop -> `RTSP_ERROR`, reconnect up to N times, then `SourceError`.
- Models: missing file / import / load failure -> `ModelLoadError` with instructions.
- DB: `DatabaseError`; events queued and retried; registration failure keeps the track unresolved to retry next cycle.
- Images: `ImageStorageError` logged as `IMAGE_ERROR`; the DB row is still written with NULL path.
- Config: `ConfigError` on any invalid/unknown key at start-up.
- Shutdown: Ctrl+C / `q` / end of file -> everyone present gets EXIT `shutdown`.

## Honest limitations to mention
Simplified tracker; identity fixed per track (no re-verification); one embedding per face; presence-based not door-line; real-model accuracy unverified until calibrated.
