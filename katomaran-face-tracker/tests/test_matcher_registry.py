import numpy as np
import pytest

from datetime import datetime

from app.database.sqlite_repository import SQLiteRepository
from app.errors import RecognitionError
from app.event_logging.event_logger import EventLogger
from app.recognition.face_matcher import FaceMatcher, normalize
from app.registration.face_registry import FaceRegistry
from app.storage.image_store import ImageStore


def vec(seed, dim=32):
    return normalize(np.random.default_rng(seed).normal(size=dim))


def noisy(v, scale=0.02, seed=0):
    return normalize(v + np.random.default_rng(seed).normal(scale=scale, size=v.shape))


@pytest.fixture
def parts(tmp_path):
    repo = SQLiteRepository(tmp_path / "faces.db")
    logger = EventLogger(tmp_path / "events.log", console=False)
    images = ImageStore(tmp_path / "logs")
    yield repo, logger, images
    repo.close()
    logger.close()


def crop():
    return np.full((40, 40, 3), 128, dtype=np.uint8)


def test_matcher_cosine_and_empty_gallery():
    m = FaceMatcher()
    assert m.best_match(vec(1)) == (None, -1.0)
    m.add("F001", vec(1))
    face_id, sim = m.best_match(vec(1) * 5)       # scale-invariant: normalised internally
    assert face_id == "F001" and sim == pytest.approx(1.0, abs=1e-5)


def test_matcher_rejects_bad_vectors():
    m = FaceMatcher()
    m.add("F001", vec(1, 32))
    with pytest.raises(RecognitionError):
        m.add("F002", vec(2, 16))                       # dimension mismatch
    with pytest.raises(RecognitionError):
        normalize(np.zeros(8))
    with pytest.raises(RecognitionError):
        normalize(np.array([np.nan, 1.0]))


def test_new_face_registered_with_f001(parts):
    repo, logger, images = parts
    reg = FaceRegistry.load(repo, images, logger, 0.45)
    result = reg.identify_or_register(vec(1), crop(), datetime.now(), track_id=5)
    assert (result.face_id, result.is_new) == ("F001", True)
    assert repo.count_faces() == 1 and reg.registered_count == 1
    assert repo.get_face("F001").representative_image_path == "registrations/" + \
        datetime.now().astimezone().strftime("%Y-%m-%d") + "/F001.jpg"


def test_duplicate_face_is_recognised_not_registered(parts):
    repo, logger, images = parts
    reg = FaceRegistry.load(repo, images, logger, 0.45)
    reg.identify_or_register(vec(1), crop(), datetime.now())
    again = reg.identify_or_register(noisy(vec(1)), crop(), datetime.now())
    assert (again.face_id, again.is_new) == ("F001", False)
    assert repo.count_faces() == 1


def test_different_person_gets_new_id(parts):
    repo, logger, images = parts
    reg = FaceRegistry.load(repo, images, logger, 0.45)
    reg.identify_or_register(vec(1), crop(), datetime.now())
    other = reg.identify_or_register(vec(2), crop(), datetime.now())
    assert other.face_id == "F002" and repo.count_faces() == 2


def test_gallery_persists_across_restart(parts):
    repo, logger, images = parts
    FaceRegistry.load(repo, images, logger, 0.45).identify_or_register(vec(1), crop(), datetime.now())
    reloaded = FaceRegistry.load(repo, images, logger, 0.45)           # "restart"
    assert reloaded.registered_count == 1
    result = reloaded.identify_or_register(noisy(vec(1), seed=3), crop(), datetime.now())
    assert (result.face_id, result.is_new) == ("F001", False)


def test_threshold_is_respected(parts):
    repo, logger, images = parts
    strict = FaceRegistry.load(repo, images, logger, 0.999999)
    strict.identify_or_register(vec(1), crop(), datetime.now())
    result = strict.identify_or_register(noisy(vec(1), scale=0.2), crop(), datetime.now())
    assert result.is_new       # same person but similarity below an absurdly strict threshold
