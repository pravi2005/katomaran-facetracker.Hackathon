from datetime import datetime

import numpy as np

from app.database.sqlite_repository import SQLiteRepository
from app.errors import DatabaseError
from app.event_logging.event_logger import EventLogger
from app.models import EventType, ExitReason, FrameTime, PresenceEvent
from app.presence.event_recorder import EventRecorder
from app.storage.image_store import ImageStore


class FlakyRepo:
    """Wraps a real repository; the first N insert_event calls fail."""

    def __init__(self, real, failures):
        self.real, self.failures = real, failures

    def insert_event(self, *args):
        if self.failures > 0:
            self.failures -= 1
            raise DatabaseError("database is locked")
        return self.real.insert_event(*args)


def event(kind=EventType.ENTRY, reason=None):
    now = datetime(2026, 10, 3, 10, 0, 0).astimezone()
    crop = np.random.default_rng(0).integers(0, 255, size=(50, 50, 3), dtype=np.uint8)
    return PresenceEvent("F001", kind, FrameTime(1.0, now, 1.0), 4, reason=reason, crop=crop)


def _setup(tmp_path):
    real = SQLiteRepository(tmp_path / "db.sqlite")
    real.create_face(np.ones(8, np.float32), "t")
    logger = EventLogger(tmp_path / "events.log", console=False)
    return real, logger, ImageStore(tmp_path / "logs")


def test_entry_and_exit_rows_images_and_log(tmp_path):
    real, logger, images = _setup(tmp_path)
    rec = EventRecorder(real, images, logger)
    rec.record(event(EventType.ENTRY))
    rec.record(event(EventType.EXIT, ExitReason.SHUTDOWN))
    rows = real.get_events()
    assert [r.event_type for r in rows] == ["ENTRY", "EXIT"]
    assert rows[1].reason == "shutdown" and rows[0].source_timestamp == "00:00:01.000"
    assert all((tmp_path / "logs" / r.image_path).is_file() for r in rows)
    log = (tmp_path / "events.log").read_text(encoding="utf-8")
    assert "ENTRY | face_id=F001" in log and "reason=shutdown" in log
    real.close(); logger.close()


def test_database_failure_is_queued_and_retried(tmp_path):
    real, logger, images = _setup(tmp_path)
    rec = EventRecorder(FlakyRepo(real, failures=2), images, logger)
    rec.record(event(EventType.ENTRY))            # fails -> queued, no exception
    assert rec.pending_count == 1 and real.get_events() == []
    rec.record(event(EventType.EXIT, ExitReason.PERSON_LEFT))   # flush retry fails again (1 failure left)
    assert rec.pending_count >= 1
    rec.flush_pending()
    rec.flush_pending()
    assert rec.pending_count == 0
    assert len(real.get_events()) == 2
    assert "DATABASE_ERROR" in (tmp_path / "events.log").read_text(encoding="utf-8")
    real.close(); logger.close()


def test_image_failure_does_not_block_database_row(tmp_path):
    real, logger, images = _setup(tmp_path)
    rec = EventRecorder(real, images, logger)
    bad = event()
    bad.crop = np.zeros((0, 0, 3), np.uint8)
    rec.record(bad)
    row = real.get_events()[0]
    assert row.image_path is None and row.event_type == "ENTRY"
    assert "IMAGE_ERROR" in (tmp_path / "events.log").read_text(encoding="utf-8")
    real.close(); logger.close()
