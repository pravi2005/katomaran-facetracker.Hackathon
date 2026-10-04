"""SQLite persistence. ALL SQL in the project lives in this file.

Tables
------
meta    key/value settings (schema version, embedding dimension, model name)
faces   one row per registered person (embedding stored as raw float32 bytes)
events  ENTRY / EXIT events

Embedding serialization format
------------------------------
* dtype: little-endian float32 ('<f4'), C-contiguous, shape (dim,)
* stored as a BLOB (``ndarray.tobytes()``), length must equal dim * 4
* ``dim`` and the model name are recorded in ``meta`` and checked on startup
  (IncompatibleEmbeddingError if a different model produced the stored data)

Resilience: WAL journal, explicit transactions, parameterized SQL only.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import numpy as np

from app.errors import DatabaseError, IncompatibleEmbeddingError
from app.models import EventRecord, FaceRecord
from app.storage.image_store import format_face_id

SCHEMA_VERSION = "1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS faces (
    face_id                   TEXT PRIMARY KEY,
    seq                       INTEGER NOT NULL UNIQUE,
    registered_at             TEXT NOT NULL,
    embedding                 BLOB NOT NULL,
    representative_image_path TEXT
);
CREATE TABLE IF NOT EXISTS events (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    face_id          TEXT NOT NULL REFERENCES faces(face_id),
    event_type       TEXT NOT NULL CHECK (event_type IN ('ENTRY', 'EXIT')),
    timestamp        TEXT NOT NULL,
    source_timestamp TEXT,
    image_path       TEXT,
    track_id         INTEGER,
    reason           TEXT CHECK (reason IS NULL OR reason IN ('person_left', 'shutdown'))
);
CREATE INDEX IF NOT EXISTS idx_events_face_id ON events(face_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
"""


def serialize_embedding(embedding: np.ndarray) -> bytes:
    return np.ascontiguousarray(embedding, dtype="<f4").tobytes()


def deserialize_embedding(blob: bytes, dim: Optional[int] = None) -> np.ndarray:
    if len(blob) % 4 != 0:
        raise DatabaseError("Corrupt embedding blob (length not a multiple of 4).")
    vector = np.frombuffer(blob, dtype="<f4").astype(np.float32)
    if dim is not None and vector.shape[0] != dim:
        raise IncompatibleEmbeddingError(
            f"Embedding has dimension {vector.shape[0]}, expected {dim}.")
    return vector


class SQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(db_path), isolation_level=None, timeout=5.0)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
            self._conn.execute(
                "INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,))
        except (sqlite3.Error, OSError) as exc:
            raise DatabaseError(f"Cannot open database {db_path}: {exc}") from exc

    # -- helpers ----------------------------------------------------------
    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            yield self._conn
            self._conn.execute("COMMIT")
        except sqlite3.Error as exc:
            self._rollback()
            raise DatabaseError(str(exc)) from exc
        except Exception:
            self._rollback()
            raise

    def _rollback(self) -> None:
        try:
            self._conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass  # no active transaction - nothing to roll back

    def _get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    # -- embedding compatibility -----------------------------------------
    def ensure_embedding_compatibility(self, dim: int, model_name: str) -> None:
        """Record the embedding model on first use; refuse a different one later."""
        try:
            stored_dim = self._get_meta("embedding_dim")
            stored_model = self._get_meta("embedding_model")
            if stored_dim is None:
                with self._transaction() as conn:
                    conn.execute("INSERT INTO meta(key, value) VALUES ('embedding_dim', ?)", (str(dim),))
                    conn.execute("INSERT INTO meta(key, value) VALUES ('embedding_model', ?)", (model_name,))
                return
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        if int(stored_dim) != dim or stored_model != model_name:
            raise IncompatibleEmbeddingError(
                f"Database was created with model '{stored_model}' (dim {stored_dim}) but the "
                f"current model is '{model_name}' (dim {dim}). Use a new database file or "
                "re-register faces; embeddings from different models cannot be compared.")

    # -- faces ------------------------------------------------------------
    def create_face(self, embedding: np.ndarray, registered_at: str) -> str:
        """Insert a new face and return its freshly generated Face ID."""
        with self._transaction() as conn:
            row = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM faces").fetchone()
            sequence = int(row["next_seq"])
            face_id = format_face_id(sequence)
            conn.execute(
                "INSERT INTO faces(face_id, seq, registered_at, embedding) VALUES (?, ?, ?, ?)",
                (face_id, sequence, registered_at, serialize_embedding(embedding)))
        return face_id

    def set_representative_image(self, face_id: str, image_path: str) -> None:
        with self._transaction() as conn:
            conn.execute("UPDATE faces SET representative_image_path = ? WHERE face_id = ?",
                         (image_path, face_id))

    def get_face(self, face_id: str) -> Optional[FaceRecord]:
        try:
            row = self._conn.execute("SELECT * FROM faces WHERE face_id = ?", (face_id,)).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        return self._row_to_face(row) if row else None

    def list_faces(self) -> List[FaceRecord]:
        try:
            rows = self._conn.execute("SELECT * FROM faces ORDER BY seq").fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        return [self._row_to_face(r) for r in rows]

    def load_embeddings(self) -> List[Tuple[str, np.ndarray]]:
        return [(f.face_id, f.embedding) for f in self.list_faces()]

    def count_faces(self) -> int:
        """The all-time unique visitor count: one row per registered person."""
        try:
            return int(self._conn.execute("SELECT COUNT(*) FROM faces").fetchone()[0])
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc

    @staticmethod
    def _row_to_face(row: sqlite3.Row) -> FaceRecord:
        return FaceRecord(face_id=row["face_id"], registered_at=row["registered_at"],
                          embedding=deserialize_embedding(row["embedding"]),
                          representative_image_path=row["representative_image_path"])

    # -- events -----------------------------------------------------------
    def insert_event(self, face_id: str, event_type: str, timestamp: str,
                     source_timestamp: Optional[str], image_path: Optional[str],
                     track_id: Optional[int], reason: Optional[str]) -> int:
        with self._transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO events(face_id, event_type, timestamp, source_timestamp, "
                "image_path, track_id, reason) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (face_id, event_type, timestamp, source_timestamp, image_path, track_id, reason))
            return int(cursor.lastrowid)

    def get_events(self, face_id: Optional[str] = None, event_type: Optional[str] = None,
                   limit: int = 1000) -> List[EventRecord]:
        sql, params = "SELECT * FROM events WHERE 1=1", []
        if face_id:
            sql += " AND face_id = ?"
            params.append(face_id)
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        sql += " ORDER BY event_id LIMIT ?"
        params.append(limit)
        try:
            rows = self._conn.execute(sql, params).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        return [EventRecord(event_id=r["event_id"], face_id=r["face_id"],
                            event_type=r["event_type"], timestamp=r["timestamp"],
                            source_timestamp=r["source_timestamp"], image_path=r["image_path"],
                            track_id=r["track_id"], reason=r["reason"]) for r in rows]

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
