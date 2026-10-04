"""End-to-end scenarios A-H from the specification, run through the REAL pipeline,
tracker, registry, presence manager, SQLite, image store and logger.
Only the video, YOLO and InsightFace are replaced by scripted fakes."""

import numpy as np
import pytest

from tests.helpers import build_harness, person_vector


@pytest.fixture
def make(tmp_path):
    created = []

    def _make(timeline, total, **kw):
        h = build_harness(tmp_path, timeline, total, **kw)
        created.append(h)
        return h
    yield _make
    for h in created:
        h.close()


def events(h, face_id=None):
    return [(e.face_id, e.event_type, e.reason) for e in h.repo.get_events(face_id=face_id)]


def test_a_new_person_enters(make):
    h = make({"A": [(0, 30)]}, 30)
    summary = h.run()
    assert [f.face_id for f in h.repo.list_faces()] == ["F001"]
    assert events(h)[0] == ("F001", "ENTRY", None)
    assert summary.unique_visitors == 1 == h.repo.count_faces()


def test_b_person_stays_visible_no_duplicates(make):
    h = make({"A": [(0, 60)]}, 60)
    h.run()
    assert h.repo.count_faces() == 1
    entries = [e for e in h.repo.get_events(event_type="ENTRY")]
    assert len(entries) == 1
    assert h.embedder.calls == 2  # embeddings are NOT recomputed for a resolved track


def test_c_temporary_disappearance_no_exit(make):
    h = make({"A": [(0, 20), (30, 50)]}, 50)   # hidden for 1.0 s < max_missing 2.0 s
    h.run()
    got = events(h)
    assert got == [("F001", "ENTRY", None), ("F001", "EXIT", "shutdown")]  # no person_left EXIT


def test_c2_track_id_switch_does_not_duplicate_entry(make):
    # hidden 1.5 s: longer than the track buffer (0.5 s) so the track dies and a NEW
    # track id appears, but shorter than max_missing (2.0 s) so presence continues.
    h = make({"A": [(0, 20), (35, 60)]}, 60)
    h.run()
    assert h.repo.count_faces() == 1
    assert len(h.repo.get_events(event_type="ENTRY")) == 1
    assert [e.reason for e in h.repo.get_events(event_type="EXIT")] == ["shutdown"]
    tracks = {e.track_id for e in h.repo.get_events()}
    assert len(tracks) >= 2  # proves the Track ID changed while the Face ID did not


def test_d_person_leaves_exactly_one_exit(make):
    h = make({"A": [(0, 20)]}, 70)
    h.run()
    assert events(h) == [("F001", "ENTRY", None), ("F001", "EXIT", "person_left")]


def test_e_reentry_same_face_id_count_unchanged(make):
    h = make({"A": [(0, 20), (60, 90)]}, 90)
    summary = h.run()
    assert events(h) == [("F001", "ENTRY", None), ("F001", "EXIT", "person_left"),
                         ("F001", "ENTRY", None), ("F001", "EXIT", "shutdown")]
    assert summary.unique_visitors == 1 == h.repo.count_faces()


def test_f_second_person_gets_f002(make):
    h = make({"A": [(0, 20)], "B": [(30, 50)]}, 50)
    summary = h.run()
    assert [f.face_id for f in h.repo.list_faces()] == ["F001", "F002"]
    assert summary.unique_visitors == 2


def test_g_two_people_simultaneously(make):
    h = make({"A": [(0, 30)], "B": [(0, 30)]}, 30)
    h.run()
    faces = {f.face_id: f.embedding for f in h.repo.list_faces()}
    assert sorted(faces) == ["F001", "F002"]
    a, b = person_vector("A"), person_vector("B")
    cos = lambda x, y: float(np.dot(x, y) / (np.linalg.norm(x) * np.linalg.norm(y)))
    assert cos(faces["F001"], a) > 0.95 and cos(faces["F002"], b) > 0.95  # identities are correct
    assert len(h.repo.get_events(event_type="ENTRY")) == 2


def test_h_database_persists_across_restart(tmp_path):
    h1 = build_harness(tmp_path, {"A": [(0, 20)]}, 30, log_name="run1.log")
    h1.run()
    h1.close()

    # "restart": brand-new objects, same database file
    h2 = build_harness(tmp_path, {"A": [(0, 20)], "B": [(10, 30)]}, 30, log_name="run2.log")
    assert h2.registry.registered_count == 1          # F001 loaded from disk
    h2.run()
    assert [f.face_id for f in h2.repo.list_faces()] == ["F001", "F002"]  # A re-recognised, B new
    assert h2.repo.count_faces() == 2
    h2.close()


def test_images_and_log_are_written(make, tmp_path):
    h = make({"A": [(0, 20)]}, 70)
    h.run()
    root = tmp_path / "logs"
    assert list((root / "registrations").rglob("F001.jpg"))
    assert list((root / "entries").rglob("F001_*.jpg"))
    assert list((root / "exits").rglob("F001_*.jpg"))
    for event in h.repo.get_events():
        assert event.image_path and (root / event.image_path).is_file()
    text = (root / "events.log").read_text(encoding="utf-8")
    for token in ("FACE_DETECTED", "TRACK_CREATED", "EMBEDDING_GENERATED", "FACE_REGISTERED",
                  "ENTRY", "EXIT", "TRACK_LOST"):
        assert token in text, token


def test_frame_skipping_reduces_detector_calls(make):
    h = make({"A": [(0, 50)]}, 50)  # skip_frames=1 -> every 2nd frame
    h.run()
    assert h.pipeline._detector.calls == 25
