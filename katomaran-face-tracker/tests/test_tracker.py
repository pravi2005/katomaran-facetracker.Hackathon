from app.models import Detection
from app.tracking.tracker import ByteTracker, iou


def det(x, y=50, size=80, conf=0.9):
    return Detection((x, y, x + size, y + size), conf)


def make(buffer=1.0):
    return ByteTracker(high_threshold=0.5, low_threshold=0.2, match_iou=0.3,
                       low_match_iou=0.5, buffer_seconds=buffer)


def test_iou_basics():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert 0.3 < iou((0, 0, 10, 10), (5, 0, 15, 10)) < 0.4


def test_new_detection_creates_track_and_keeps_id_while_moving():
    t = make()
    new, _ = t.update([det(100)], now=0.0)
    assert [tr.track_id for tr in new] == [1]
    for step in range(1, 6):
        t.predict()
        new, removed = t.update([det(100 + 4 * step)], now=step * 0.1)
        assert new == [] and removed == []
    assert [tr.track_id for tr in t.tracks] == [1] and t.tracks[0].hits == 6


def test_two_faces_get_distinct_ids():
    t = make()
    new, _ = t.update([det(20), det(200)], now=0.0)
    assert sorted(tr.track_id for tr in new) == [1, 2]


def test_coasting_moves_box_between_detections():
    t = make()
    t.update([det(100)], 0.0)
    t.predict()
    t.update([det(110)], 0.1)             # learns velocity ~ +5 px/frame
    before = t.tracks[0].bbox[0]
    t.predict()                            # no detection this frame
    assert t.tracks[0].bbox[0] > before and not t.tracks[0].matched_this_update


def test_track_removed_only_after_buffer():
    t = make(buffer=1.0)
    t.update([det(100)], 0.0)
    _, removed = t.update([], 0.5)
    assert removed == [] and len(t.tracks) == 1     # temporary loss tolerated
    _, removed = t.update([], 1.5)
    assert [r.track_id for r in removed] == [1] and t.tracks == []


def test_low_confidence_detection_keeps_track_alive():
    t = make(buffer=0.3)
    t.update([det(100)], 0.0)
    t.predict()
    t.update([det(102, conf=0.3)], 0.5)    # low score (0.2..0.5) but overlaps strongly
    assert len(t.tracks) == 1 and t.tracks[0].track_id == 1
    assert t.tracks[0].last_matched_at == 0.5


def test_low_confidence_alone_does_not_start_track():
    t = make()
    new, _ = t.update([det(100, conf=0.3)], 0.0)
    assert new == [] and t.tracks == []


def test_ids_are_never_reused():
    t = make(buffer=0.1)
    t.update([det(100)], 0.0)
    t.update([], 1.0)                      # track 1 removed
    new, _ = t.update([det(100)], 2.0)
    assert new[0].track_id == 2


def test_drain_empties_tracker():
    t = make()
    t.update([det(20), det(200)], 0.0)
    assert len(t.drain()) == 2 and t.tracks == []
