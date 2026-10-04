import numpy as np

from app.config import QualityConfig
from app.recognition.quality import QualityChecker


def noise(h=200, w=200):
    return np.random.default_rng(0).integers(0, 255, size=(h, w, 3), dtype=np.uint8)


def checker(**kw):
    return QualityChecker(QualityConfig(**kw))


def test_good_face_passes():
    assert checker().check(noise(), (50, 50, 150, 150), 0.9).ok


def test_rejections():
    img = noise()
    assert checker().check(img, (50, 50, 150, 150), 0.3).reason == "low_confidence"
    assert checker().check(img, (50, 50, 80, 80), 0.9).reason == "too_small"
    assert checker().check(img, (0, 50, 100, 150), 0.9).reason == "touches_frame_edge"
    assert checker(reject_edge_touching=False).check(img, (0, 50, 100, 150), 0.9).ok
    flat = np.full((200, 200, 3), 120, np.uint8)
    assert checker().check(flat, (50, 50, 150, 150), 0.9).reason == "too_blurry"
