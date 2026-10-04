import json

import pytest

from app.config import load_config, redact_url, resolve_source
from app.errors import ConfigError


def write(tmp_path, data, name="config.json"):
    path = tmp_path / name
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return path


def test_shipped_config_is_valid():
    from pathlib import Path
    cfg = load_config(Path(__file__).resolve().parents[1] / "config.json")
    assert cfg.detection.skip_frames == 4 and cfg.tracking.max_missing_seconds == 2.0


def test_defaults_fill_missing_sections(tmp_path):
    cfg = load_config(write(tmp_path, {"detection": {"skip_frames": 2}}))
    assert cfg.detection.skip_frames == 2 and cfg.recognition.similarity_threshold == 0.45


def test_missing_file():
    with pytest.raises(ConfigError, match="not found"):
        load_config("does_not_exist.json")


def test_invalid_json(tmp_path):
    with pytest.raises(ConfigError, match="Invalid JSON"):
        load_config(write(tmp_path, "{ not json"))


@pytest.mark.parametrize("data", [
    {"detection": {"skip_frames": -1}},
    {"detection": {"confidence_threshold": 1.5}},
    {"recognition": {"similarity_threshold": 3}},
    {"tracking": {"max_missing_seconds": 0}},
    {"input": {"source_type": "ftp"}},
    {"counting": {"scope": "forever"}},
    {"storage": {"jpeg_quality": 0}},
    {"recognition": {"embeddings_per_decision": 5, "max_resolve_attempts": 2}},
])
def test_out_of_range_values_rejected(tmp_path, data):
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, data))


def test_wrong_type_and_unknown_keys(tmp_path):
    with pytest.raises(ConfigError, match="must be int"):
        load_config(write(tmp_path, {"detection": {"skip_frames": "four"}}))
    with pytest.raises(ConfigError, match="Unknown key"):
        load_config(write(tmp_path, {"detection": {"skipframes": 4}}))
    with pytest.raises(ConfigError, match="Unknown top-level"):
        load_config(write(tmp_path, {"detecton": {}}))


def test_int_accepted_for_float_fields(tmp_path):
    assert load_config(write(tmp_path, {"tracking": {"max_missing_seconds": 3}})).tracking.max_missing_seconds == 3.0


def test_env_source_and_dotenv(tmp_path, monkeypatch):
    monkeypatch.delenv("TEST_RTSP", raising=False)
    (tmp_path / ".env").write_text("TEST_RTSP=rtsp://user:pw@10.0.0.5:554/stream\n", encoding="utf-8")
    cfg = load_config(write(tmp_path, {"input": {"source": "env:TEST_RTSP", "source_type": "rtsp"}}))
    assert resolve_source(cfg).startswith("rtsp://user:pw@")


def test_env_source_missing_variable(tmp_path, monkeypatch):
    monkeypatch.delenv("NOPE_URL", raising=False)
    cfg = load_config(write(tmp_path, {"input": {"source": "env:NOPE_URL", "source_type": "rtsp"}}))
    with pytest.raises(ConfigError, match="NOPE_URL"):
        resolve_source(cfg)


def test_video_path_resolved_relative_to_config(tmp_path):
    cfg = load_config(write(tmp_path, {"input": {"source": "clips/a.mp4"}}))
    assert resolve_source(cfg) == str(tmp_path / "clips" / "a.mp4")


def test_redact_url_hides_credentials():
    assert redact_url("rtsp://admin:secret@192.168.1.5:554/live") == "rtsp://***@192.168.1.5:554/live"
    assert "secret" not in redact_url("rtsp://admin:secret@cam/live")
    assert redact_url("rtsp://cam/live") == "rtsp://cam/live"
