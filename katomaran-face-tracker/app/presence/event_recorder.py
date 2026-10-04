"""Turns PresenceEvents into: image file + database row + log line.

Resilience rules
----------------
* An image failure never blocks the database row (image_path becomes NULL).
* A database failure never crashes the pipeline: the event is kept in a small
  in-memory queue and retried on the next call / at shutdown.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Optional

from app.database.sqlite_repository import SQLiteRepository
from app.errors import DatabaseError, ImageStorageError
from app.event_logging import event_logger as ev
from app.event_logging.event_logger import EventLogger
from app.models import EventType, PresenceEvent, format_source_timestamp, format_wall_time
from app.storage.image_store import ImageStore

MAX_PENDING_EVENTS = 1000


class EventRecorder:
    def __init__(self, repository: SQLiteRepository, image_store: ImageStore,
                 logger: EventLogger) -> None:
        self._repo = repository
        self._images = image_store
        self._log = logger
        self._pending: Deque[tuple] = deque(maxlen=MAX_PENDING_EVENTS)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def record(self, event: PresenceEvent) -> None:
        self.flush_pending()
        image_path = self._save_image(event)
        row = (event.face_id, event.event_type.value, format_wall_time(event.time.wall_time),
               format_source_timestamp(event.time.source_seconds), image_path,
               event.track_id, event.reason.value if event.reason else None)
        self._write_row(row)
        fields = dict(face_id=event.face_id, track_id=event.track_id, image=image_path or "none")
        if event.reason:
            fields["reason"] = event.reason.value
        if event.absent_seconds is not None and event.event_type is EventType.EXIT:
            fields["absent_seconds"] = event.absent_seconds
        src = format_source_timestamp(event.time.source_seconds)
        if src:
            fields["video_time"] = src
        self._log.info(event.event_type.value, **fields)

    def flush_pending(self) -> None:
        while self._pending:
            row = self._pending[0]
            try:
                self._repo.insert_event(*row)
            except DatabaseError:
                return  # still failing; keep the queue for later
            self._pending.popleft()

    def _save_image(self, event: PresenceEvent) -> Optional[str]:
        if event.crop is None:
            return None
        try:
            save = (self._images.save_entry if event.event_type is EventType.ENTRY
                    else self._images.save_exit)
            return save(event.face_id, event.crop, event.time.wall_time)
        except ImageStorageError as exc:
            self._log.error(ev.IMAGE_ERROR, face_id=event.face_id, error=str(exc))
            return None

    def _write_row(self, row: tuple) -> None:
        try:
            self._repo.insert_event(*row)
        except DatabaseError as exc:
            self._pending.append(row)
            self._log.error(ev.DATABASE_ERROR, operation="insert_event", face_id=row[0],
                            error=str(exc), queued=len(self._pending))
