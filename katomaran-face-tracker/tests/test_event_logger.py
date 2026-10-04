
import numpy as np
import pytest

from app.errors import ConfigError
from app.event_logging.event_logger import EventLogger


def test_log_file_created_with_structured_lines(tmp_path):
    path = tmp_path / "nested" / "events.log"
    logger = EventLogger(path, console=False)
    logger.info("FACE_REGISTERED", face_id="F001", track_id=17, best_similarity=0.123456)
    logger.error("DATABASE_ERROR", error="disk full today")
    logger.close()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    parts = [p.strip() for p in lines[0].split("|")]
    assert parts[1] == "INFO" and parts[2] == "FACE_REGISTERED"
    assert parts[3] == "face_id=F001 track_id=17 best_similarity=0.123"
    assert "| ERROR | DATABASE_ERROR | error=\"disk full today\"" in lines[1]


def test_embeddings_are_never_logged(tmp_path):
    path = tmp_path / "events.log"
    logger = EventLogger(path, console=False)
    secret = np.array([0.111111, 0.222222, 0.333333])
    logger.info("EMBEDDING_GENERATED", embedding=secret)
    logger.close()
    text = path.read_text(encoding="utf-8")
    assert "0.111" not in text and "<array omitted>" in text


def test_level_filtering(tmp_path):
    path = tmp_path / "events.log"
    logger = EventLogger(path, level="WARNING", console=False)
    logger.info("IGNORED")
    logger.warning("KEPT")
    logger.close()
    text = path.read_text(encoding="utf-8")
    assert "KEPT" in text and "IGNORED" not in text


def test_lines_are_flushed_immediately(tmp_path):
    path = tmp_path / "events.log"
    logger = EventLogger(path, console=False)
    logger.info("ENTRY", face_id="F001")
    assert "ENTRY" in path.read_text(encoding="utf-8")   # visible before close() => crash-safe
    logger.close()


def test_unwritable_log_location(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(ConfigError):
        EventLogger(blocker / "events.log", console=False)
