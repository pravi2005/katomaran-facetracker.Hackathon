from datetime import datetime

from app.models import EventType, ExitReason, FrameTime, Observation, PresenceState
from app.presence.presence_manager import PresenceManager


def ft(seconds: float) -> FrameTime:
    return FrameTime(seconds, datetime(2026, 10, 3, 10, 0, 0).astimezone(), seconds)


def obs(face_id="F001", track_id=1, conf=0.9):
    return Observation(face_id, track_id, conf)


def test_first_appearance_emits_one_entry():
    pm = PresenceManager(2.0)
    events = pm.update(ft(0), [obs()])
    assert [(e.face_id, e.event_type) for e in events] == [("F001", EventType.ENTRY)]
    assert pm.state_of("F001") is PresenceState.PRESENT


def test_continued_presence_no_more_entries():
    pm = PresenceManager(2.0)
    pm.update(ft(0), [obs()])
    for t in range(1, 20):
        assert pm.update(ft(t * 0.1), [obs()]) == []
        assert pm.expire(ft(t * 0.1)) == []


def test_temporary_disappearance_is_missing_not_exit():
    pm = PresenceManager(2.0)
    pm.update(ft(0), [obs()])
    assert pm.update(ft(0.5), []) == []
    assert pm.state_of("F001") is PresenceState.MISSING
    assert pm.expire(ft(1.9)) == []
    assert pm.update(ft(2.0), [obs(track_id=7)]) == []          # back, new track id, no event
    assert pm.state_of("F001") is PresenceState.PRESENT


def test_timeout_emits_exactly_one_exit():
    pm = PresenceManager(2.0)
    pm.update(ft(0), [obs()])
    pm.update(ft(0.5), [])
    events = pm.expire(ft(2.6))
    assert len(events) == 1 and events[0].event_type is EventType.EXIT
    assert events[0].reason is ExitReason.PERSON_LEFT
    assert pm.expire(ft(5.0)) == [] and pm.state_of("F001") is PresenceState.ABSENT


def test_reentry_gives_new_entry():
    pm = PresenceManager(1.0)
    pm.update(ft(0), [obs()])
    pm.update(ft(0.2), [])
    pm.expire(ft(2.0))
    events = pm.update(ft(3.0), [obs(track_id=9)])
    assert [e.event_type for e in events] == [EventType.ENTRY]


def test_shutdown_closes_open_sessions_with_reason():
    pm = PresenceManager(2.0)
    pm.update(ft(0), [obs("F001"), obs("F002", 2)])
    events = pm.shutdown(ft(1))
    assert [(e.face_id, e.reason) for e in events] == [("F001", ExitReason.SHUTDOWN),
                                                       ("F002", ExitReason.SHUTDOWN)]
    assert pm.shutdown(ft(2)) == []


def test_two_tracks_same_face_single_entry():
    pm = PresenceManager(2.0)
    events = pm.update(ft(0), [obs("F001", 1, 0.8), obs("F001", 2, 0.95)])
    assert len(events) == 1 and events[0].track_id == 2   # higher confidence kept


def test_invalid_timeout_rejected():
    import pytest
    with pytest.raises(ValueError):
        PresenceManager(0)
