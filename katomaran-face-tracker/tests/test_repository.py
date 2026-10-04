import numpy as np
import pytest

from app.database.sqlite_repository import (SQLiteRepository, deserialize_embedding,
                                            serialize_embedding)
from app.errors import DatabaseError, IncompatibleEmbeddingError


@pytest.fixture
def repo(tmp_path):
    r = SQLiteRepository(tmp_path / "db" / "faces.db")  # parent folder is created automatically
    yield r
    r.close()


def vec(seed, dim=16):
    v = np.random.default_rng(seed).normal(size=dim).astype(np.float32)
    return v / np.linalg.norm(v)


def test_insert_and_retrieve_face(repo):
    face_id = repo.create_face(vec(1), "2026-10-03T10:00:00.000+05:30")
    assert face_id == "F001"
    record = repo.get_face("F001")
    assert record.registered_at.startswith("2026-10-03")
    np.testing.assert_array_equal(record.embedding, vec(1))      # exact round trip
    assert record.representative_image_path is None
    repo.set_representative_image("F001", "registrations/2026-10-03/F001.jpg")
    assert repo.get_face("F001").representative_image_path.endswith("F001.jpg")
    assert repo.get_face("F999") is None


def test_ids_are_sequential_and_count(repo):
    ids = [repo.create_face(vec(i), "t") for i in range(3)]
    assert ids == ["F001", "F002", "F003"] and repo.count_faces() == 3


def test_persistence_after_reopen(tmp_path):
    path = tmp_path / "faces.db"
    r1 = SQLiteRepository(path)
    r1.create_face(vec(1), "t")
    r1.close()
    r2 = SQLiteRepository(path)
    assert r2.count_faces() == 1
    assert r2.create_face(vec(2), "t") == "F002"   # ID generation continues from the database
    r2.close()


def test_insert_and_query_events(repo):
    repo.create_face(vec(1), "t")
    first = repo.insert_event("F001", "ENTRY", "2026-10-03T10:00:00.000+05:30", "00:00:01.500",
                              "entries/x.jpg", 3, None)
    repo.insert_event("F001", "EXIT", "2026-10-03T10:05:00.000+05:30", None, None, 3, "person_left")
    assert first == 1
    assert [e.event_type for e in repo.get_events("F001")] == ["ENTRY", "EXIT"]
    only_exit = repo.get_events(event_type="EXIT")[0]
    assert only_exit.reason == "person_left" and only_exit.source_timestamp is None


def test_constraints_are_enforced(repo):
    repo.create_face(vec(1), "t")
    with pytest.raises(DatabaseError):
        repo.insert_event("F001", "WALKED", "t", None, None, 1, None)          # bad event_type
    with pytest.raises(DatabaseError):
        repo.insert_event("F001", "EXIT", "t", None, None, 1, "bad_reason")    # bad reason
    with pytest.raises(DatabaseError):
        repo.insert_event("F404", "ENTRY", "t", None, None, 1, None)           # unknown face (FK)
    assert repo.get_events() == []   # failed inserts were rolled back


def test_embedding_compatibility_check(repo):
    repo.ensure_embedding_compatibility(512, "insightface/buffalo_l")
    repo.ensure_embedding_compatibility(512, "insightface/buffalo_l")   # same model: fine
    with pytest.raises(IncompatibleEmbeddingError):
        repo.ensure_embedding_compatibility(128, "other/model")


def test_embedding_serialization_validation():
    blob = serialize_embedding(vec(3, 8))
    assert len(blob) == 32
    assert deserialize_embedding(blob, dim=8).shape == (8,)
    with pytest.raises(IncompatibleEmbeddingError):
        deserialize_embedding(blob, dim=512)
    with pytest.raises(DatabaseError):
        deserialize_embedding(b"abc")


def test_cannot_open_unwritable_path(tmp_path):
    blocker = tmp_path / "file.txt"
    blocker.write_text("x")
    with pytest.raises(DatabaseError):
        SQLiteRepository(blocker / "faces.db")   # parent is a file
