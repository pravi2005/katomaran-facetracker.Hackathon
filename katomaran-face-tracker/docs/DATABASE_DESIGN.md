# Database design (SQLite)

File: `data/faces.db` (git-ignored). Journal mode WAL, `synchronous=NORMAL`, foreign keys ON. All SQL is in `app/database/sqlite_repository.py` and is parameterized. Writes use explicit `BEGIN IMMEDIATE ... COMMIT` transactions and roll back on error.

## faces

| Column | Type | Why |
|---|---|---|
| `face_id` | TEXT PK | Permanent identity `F001`, `F002`, ... |
| `seq` | INTEGER UNIQUE | Numeric part; next ID = `MAX(seq)+1` inside the transaction, so IDs survive restarts (no in-memory counter) |
| `registered_at` | TEXT | ISO-8601 local time with UTC offset, ms precision |
| `embedding` | BLOB | Registration embedding (see format below) |
| `representative_image_path` | TEXT NULL | Relative path of the sharpest crop; NULL if image saving failed |

## events

| Column | Type | Why |
|---|---|---|
| `event_id` | INTEGER PK AUTOINCREMENT | Order of events |
| `face_id` | TEXT FK -> faces | Who |
| `event_type` | TEXT CHECK `ENTRY`/`EXIT` | Invalid values rejected by the database |
| `timestamp` | TEXT | **Wall-clock** time the event was recorded (local, ISO-8601 with offset) |
| `source_timestamp` | TEXT NULL | **Position in the source video** `HH:MM:SS.mmm`; NULL for RTSP |
| `image_path` | TEXT NULL | Relative path of the saved crop (NULL if image failed) |
| `track_id` | INTEGER NULL | Debugging only; not an identity |
| `reason` | TEXT NULL CHECK `person_left`/`shutdown` | EXIT reason; NULL for ENTRY |

Indexes: `events(face_id)`, `events(timestamp)`.

For a video file the wall-clock time is *when it was processed*, the source timestamp is *where in the video it happened*. For EXIT, the timestamp is the moment the exit was confirmed (roughly `max_missing_seconds` after the person was last seen); the log line also shows `absent_seconds`.

## meta

Key/value: `schema_version`, `embedding_dim`, `embedding_model`. Checked at start-up; a database created by another model/dimension is refused instead of silently producing wrong matches.

## Embedding serialization

- dtype: little-endian `float32` (`<f4`), C-contiguous, shape `(dim,)`; `ndarray.tobytes()`.
- `dim` comes from the model at runtime (not hard-coded) and is stored in `meta`.
- Reading: `np.frombuffer(blob, dtype='<f4')`; blob length must be a multiple of 4 and match `dim`.
- Stored vectors are L2-normalised.

## Images

Images are never stored in SQLite. Paths are relative to `storage.root` (posix style). Layout: `entries/`, `exits/`, `registrations/` by date.

## Unique visitor count

`SELECT COUNT(*) FROM faces` = number of distinct people ever registered in this database (`counting.scope = all_time`). `session` scope counts distinct Face IDs seen in the current run (kept in memory). Re-identification never inserts into `faces`.

## Resilience

- Registration: DB row first, then image, then `UPDATE` of the image path (an image failure leaves a valid face row).
- Events: if the insert fails (`DatabaseError`), the row is queued (max 1000) and retried on the next event and at shutdown; `DATABASE_ERROR` is logged.
- Not covered: a database that stays broken for the whole run loses queued events beyond the queue size when the process exits.
