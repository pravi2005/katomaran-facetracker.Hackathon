"""Video analysis service for Katomaran dashboard.

Accepts an uploaded video, runs it through the existing AI pipeline in a
subprocess (so that model globals / signal handlers never collide with
FastAPI's event loop), and returns a structured analysis report.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from config import TRACKER_DIR, DB_PATH

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
UPLOADS_DIR = TRACKER_DIR.parent / "katomaran-dashboard" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ANALYSES_DIR = TRACKER_DIR.parent / "katomaran-dashboard" / "analyses"
ANALYSES_DIR.mkdir(parents=True, exist_ok=True)

TRACKER_CONFIG = TRACKER_DIR / "config.json"

# ---------------------------------------------------------------------------
# In-memory analysis registry (lives for the server process lifetime)
# ---------------------------------------------------------------------------
_analyses: Dict[str, "Analysis"] = {}
_lock = Lock()

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class AnalysisRecord:
    analysis_id: str
    filename: str
    status: str  # pending | running | completed | failed
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None
    video_path: Optional[str] = None
    db_path: Optional[str] = None
    log_path: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_analysis(filename: str, video_path: Path) -> AnalysisRecord:
    analysis_id = str(uuid.uuid4())[:8].upper()
    rec = AnalysisRecord(
        analysis_id=analysis_id,
        filename=filename,
        status="pending",
        created_at=_iso_now(),
        video_path=str(video_path),
    )
    with _lock:
        _analyses[analysis_id] = rec
    return rec


def get_analysis(analysis_id: str) -> Optional[AnalysisRecord]:
    with _lock:
        return _analyses.get(analysis_id)


def list_analyses() -> List[AnalysisRecord]:
    with _lock:
        return sorted(_analyses.values(), key=lambda r: r.created_at, reverse=True)


def run_analysis(rec: AnalysisRecord) -> None:
    """Run the existing AI pipeline in a subprocess against the uploaded video.

    Uses a dedicated SQLite database per analysis so results are isolated from
    the main demo data while reusing all existing recognition data.
    """
    analysis_id = rec.analysis_id
    video_path = Path(rec.video_path)

    # Per-analysis SQLite database and log file
    analysis_dir = ANALYSES_DIR / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)

    db_file = analysis_dir / "faces.db"
    log_file = analysis_dir / "events.log"

    rec.db_path = str(db_file)
    rec.log_path = str(log_file)
    rec.status = "running"
    rec.started_at = _iso_now()

    # Build subprocess args — reuse the existing pipeline exactly
    cmd = [
        sys.executable, "-m", "app.main",
        "--config", str(TRACKER_CONFIG),
        "--source", str(video_path),
        "--db", str(db_file),
        "--no-display",
    ]

    # Override the log file via environment so the log doesn't pollute the main log
    import os
    env = os.environ.copy()
    # We pass a patched config override via a temp config file so the log file
    # path is also isolated. Minimal — only change source, db, logging.file.
    tmp_cfg = _build_analysis_config(video_path, db_file, log_file)
    tmp_cfg_path = analysis_dir / "config.json"
    tmp_cfg_path.write_text(json.dumps(tmp_cfg, indent=2), encoding="utf-8")

    cmd = [
        sys.executable, "-m", "app.main",
        "--config", str(tmp_cfg_path),
        "--no-display",
    ]

    t0 = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(TRACKER_DIR),
            capture_output=True,
            text=True,
            timeout=3600,  # 1-hour hard limit
            env=env,
        )
        elapsed = time.monotonic() - t0

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            rec.status = "failed"
            rec.error = (stderr[-2000:] if stderr else "Pipeline exited with error.").strip()
        else:
            rec.status = "completed"
            rec.metrics = _parse_metrics(stdout)
            rec.metrics["processing_seconds"] = round(elapsed, 1)
            rec.summary = _build_summary(db_file, rec.metrics)

    except subprocess.TimeoutExpired:
        rec.status = "failed"
        rec.error = "Processing timed out (> 1 hour)."
    except Exception as exc:
        rec.status = "failed"
        rec.error = str(exc)
    finally:
        rec.finished_at = _iso_now()


def get_report(rec: AnalysisRecord) -> Dict[str, Any]:
    """Build full report dict from an analysis record."""
    if rec.status != "completed":
        return {"analysis_id": rec.analysis_id, "status": rec.status, "error": rec.error}

    db_file = Path(rec.db_path) if rec.db_path else None
    visitors = _query_visitors(db_file)
    events = _query_events(db_file)
    registrations = _query_registrations(db_file)

    return {
        "analysis_id": rec.analysis_id,
        "filename": rec.filename,
        "status": rec.status,
        "created_at": rec.created_at,
        "started_at": rec.started_at,
        "finished_at": rec.finished_at,
        "metrics": rec.metrics,
        "summary": rec.summary,
        "visitors": visitors,
        "events": events,
        "registrations": registrations,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_analysis_config(video_path: Path, db_file: Path, log_file: Path) -> dict:
    """Load the base config.json and patch only source/db/logging paths."""
    base = json.loads(TRACKER_CONFIG.read_text(encoding="utf-8"))
    base["input"] = base.get("input", {})
    base["input"]["source"] = str(video_path)
    base["input"]["source_type"] = "video"
    base["database"] = {"path": str(db_file)}
    base["logging"] = {
        "file": str(log_file),
        "level": "INFO",
        "console": False,
    }
    base["display"] = {"enabled": False, "window_name": "Analysis"}

    # Resolve detection.model to absolute so it works regardless of cwd
    model_rel = base.get("detection", {}).get("model", "models/yolov8n-face.pt")
    model_abs = (TRACKER_DIR / model_rel).resolve()
    if "detection" not in base:
        base["detection"] = {}
    base["detection"]["model"] = str(model_abs)

    # Resolve storage.root to absolute
    storage_rel = base.get("storage", {}).get("root", "logs")
    storage_abs = (TRACKER_DIR / storage_rel).resolve()
    if "storage" not in base:
        base["storage"] = {}
    base["storage"]["root"] = str(storage_abs)

    return base


def _parse_metrics(stdout: str) -> Dict[str, Any]:
    """Extract key metrics from the pipeline stdout summary block."""
    metrics: Dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        kv_map = {
            "frames": "frames_processed",
            "avg_fps": "avg_fps",
            "unique_visitors": "unique_visitors",
            "faces_detected": "faces_detected",
            "tracks_created": "tracks_created",
            "registered": "faces_registered",
        }
        for key, out_key in kv_map.items():
            if f"{key}=" in line:
                for token in line.split():
                    if token.startswith(f"{key}="):
                        try:
                            val = token.split("=", 1)[1].strip(",'\"")
                            metrics[out_key] = float(val) if "." in val else int(val)
                        except ValueError:
                            pass
    return metrics


def _build_summary(db_file: Optional[Path], metrics: Dict[str, Any]) -> Dict[str, Any]:
    if not db_file or not db_file.is_file():
        return metrics

    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        face_count = cur.execute("SELECT COUNT(*) FROM faces").fetchone()[0]
        entry_count = cur.execute("SELECT COUNT(*) FROM events WHERE event_type='ENTRY'").fetchone()[0]
        exit_count = cur.execute("SELECT COUNT(*) FROM events WHERE event_type='EXIT'").fetchone()[0]
        conn.close()

        return {
            **metrics,
            "unique_visitors": face_count,
            "entry_events": entry_count,
            "exit_events": exit_count,
        }
    except Exception:
        return metrics


def _query_visitors(db_file: Optional[Path]) -> List[Dict]:
    if not db_file or not db_file.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT f.face_id, f.registered_at,
                   COUNT(DISTINCT CASE WHEN e.event_type='ENTRY' THEN e.event_id END) AS visit_count,
                   MIN(e.timestamp) AS first_seen,
                   MAX(e.timestamp) AS last_seen,
                   f.representative_image_path
            FROM faces f
            LEFT JOIN events e ON f.face_id = e.face_id
            GROUP BY f.face_id
            ORDER BY f.registered_at
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _query_events(db_file: Optional[Path]) -> List[Dict]:
    if not db_file or not db_file.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT event_id, face_id, event_type, timestamp, reason, track_id, image_path
            FROM events
            ORDER BY timestamp
            LIMIT 500
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _query_registrations(db_file: Optional[Path]) -> List[Dict]:
    if not db_file or not db_file.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT face_id, registered_at, representative_image_path
            FROM faces
            ORDER BY registered_at
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
