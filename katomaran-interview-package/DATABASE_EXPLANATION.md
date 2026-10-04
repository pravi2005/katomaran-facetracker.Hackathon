# Database explanation

## Tables (see project `docs/DATABASE_DESIGN.md`)
- `faces(face_id PK, seq UNIQUE, registered_at, embedding BLOB, representative_image_path)`
- `events(event_id PK, face_id FK, event_type CHECK ENTRY/EXIT, timestamp, source_timestamp, image_path, track_id, reason CHECK person_left/shutdown)`
- `meta(key, value)`: `schema_version`, `embedding_dim`, `embedding_model`

## Questions you may get
**Why SQLite?** Single process, no server, built into Python, enough for the prototype. Limit: one writer at a time; multi-camera at scale would need PostgreSQL.

**Why not store images in the DB?** Large binary data bloats and slows the DB; files are easy to inspect, and the DB holds relative paths.

**How are Face IDs generated?** Inside a `BEGIN IMMEDIATE` transaction: `SELECT COALESCE(MAX(seq),0)+1`, format `F{seq:03d}`, insert. Survives restarts because it reads the database, not a counter in memory.

**How is the embedding stored?** `float32` little-endian bytes (`ndarray.tobytes()`), dimension from the model (512 for `buffalo_l`, measured at runtime, recorded in `meta`). On startup a different model/dimension raises `IncompatibleEmbeddingError`.

**What makes writes resilient?** WAL journal mode, `synchronous=NORMAL`, explicit transactions with rollback, parameterized SQL, CHECK and FOREIGN KEY constraints, and an in-memory retry queue in `EventRecorder` (max 1000) for failed event inserts.

**How is the unique count computed?** `SELECT COUNT(*) FROM faces` (scope `all_time`) - one row per registered person. Re-identification never inserts a face row. Scope `session` counts distinct Face IDs seen in this run (in memory).

**What do the two timestamps mean?** `timestamp` = wall clock when recorded (local time + offset); `source_timestamp` = position in the video (`HH:MM:SS.mmm`), NULL for RTSP. For a video file the wall time is when you processed it.

**Weak points?** The EXIT timestamp is the confirmation time (about `max_missing_seconds` after last seen). Events still in the retry queue are lost if the process dies while the DB is down.

## Useful queries
```sql
SELECT COUNT(*) FROM faces;
SELECT face_id, event_type, reason, timestamp, source_timestamp FROM events ORDER BY event_id;
SELECT face_id, COUNT(*) AS visits FROM events WHERE event_type='ENTRY' GROUP BY face_id;
```
