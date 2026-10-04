import time

import cv2
import numpy as np
import pytest

from app.errors import SourceError
from app.event_logging.event_logger import EventLogger
from app.input.video_source import FileVideoSource, RTSPVideoSource, is_valid_frame


def make_video(path, frames=12, fps=10.0):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (64, 48))
    if not writer.isOpened():
        pytest.skip("OpenCV build cannot write MJPG video here")
    for i in range(frames):
        writer.write(np.full((48, 64, 3), i * 10, dtype=np.uint8))
    writer.release()


def test_missing_file(tmp_path):
    with pytest.raises(SourceError, match="not found"):
        FileVideoSource(tmp_path / "nope.mp4").open()


def test_corrupt_file(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_text("this is not a video")
    with pytest.raises(SourceError, match="cannot open"):
        FileVideoSource(bad).open()


def test_reads_all_frames_then_none_with_timestamps(tmp_path):
    path = tmp_path / "v.avi"
    make_video(path, frames=12, fps=10.0)
    with FileVideoSource(path) as src:
        assert src.fps == pytest.approx(10.0)
        frames = []
        while (f := src.read()) is not None:
            frames.append(f)
        assert src.read() is None                      # stays at end
    assert len(frames) == 12 and frames[0].index == 0
    assert frames[5].time.source_seconds == pytest.approx(0.5)
    assert frames[5].time.stream_seconds == frames[5].time.source_seconds   # file: video clock
    assert frames[0].image.shape == (48, 64, 3)


def test_close_is_idempotent_and_read_before_open_fails(tmp_path):
    path = tmp_path / "v.avi"
    make_video(path)
    src = FileVideoSource(path)
    with pytest.raises(SourceError):
        src.read()
    src.open()
    src.close()
    src.close()


def test_frame_validation():
    assert not is_valid_frame(None)
    assert not is_valid_frame(np.zeros((0, 0, 3), np.uint8))
    assert is_valid_frame(np.zeros((4, 4, 3), np.uint8))


# ---- RTSP with a fake capture (no network needed) -------------------------

class FakeCapture:
    def __init__(self, opened=True, frames=3):
        self._opened, self._frames = opened, frames

    def isOpened(self):
        return self._opened

    def get(self, prop):
        return 25.0

    def read(self):
        if self._frames > 0:
            self._frames -= 1
            time.sleep(0.01)
            return True, np.zeros((10, 10, 3), np.uint8)
        time.sleep(0.01)
        return False, None

    def release(self):
        self._opened = False


def logger(tmp_path):
    return EventLogger(tmp_path / "events.log", console=False)


def test_rtsp_connect_failure_raises_and_hides_credentials(tmp_path):
    log = logger(tmp_path)
    src = RTSPVideoSource("rtsp://admin:topsecret@10.0.0.9/stream", log, reconnect_max_attempts=1,
                          reconnect_delay_seconds=0.0, capture_factory=lambda url: FakeCapture(opened=False))
    with pytest.raises(SourceError) as info:
        src.open()
    log.close()
    assert "topsecret" not in str(info.value)
    text = (tmp_path / "events.log").read_text(encoding="utf-8")
    assert "RTSP_ERROR" in text and "topsecret" not in text


def test_rtsp_delivers_newest_frames_and_stops_cleanly(tmp_path):
    log = logger(tmp_path)
    src = RTSPVideoSource("rtsp://cam/stream", log, reconnect_max_attempts=0, read_timeout_seconds=2.0,
                          capture_factory=lambda url: FakeCapture(frames=50))
    src.open()
    frame = src.read()
    assert frame.time.source_seconds is None and frame.time.stream_seconds >= 0
    src.close()
    log.close()


def test_rtsp_lost_stream_raises_after_failed_reconnects(tmp_path):
    log = logger(tmp_path)
    calls = {"n": 0}

    def factory(url):
        calls["n"] += 1
        return FakeCapture(opened=calls["n"] == 1, frames=2)   # first connect ok, reconnects fail

    src = RTSPVideoSource("rtsp://cam/stream", log, reconnect_max_attempts=2,
                          reconnect_delay_seconds=0.0, read_timeout_seconds=2.0, capture_factory=factory)
    src.open()
    with pytest.raises(SourceError, match="lost"):
        for _ in range(100):
            src.read()
    src.close()
    log.close()
    assert "stream_lost" in (tmp_path / "events.log").read_text(encoding="utf-8")
