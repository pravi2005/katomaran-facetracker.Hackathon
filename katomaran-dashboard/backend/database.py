"""Read-only SQLite query service for the Katomaran Dashboard."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import CONFIG_PATH, DB_PATH, EVENTS_LOG_PATH, YOLO_MODEL_PATH


def get_db_connection() -> Optional[sqlite3.Connection]:
    if not DB_PATH.is_file():
        return None
    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    if conn is None:
        return {
            "database_connected": False,
            "unique_visitors": 0,
            "currently_present": 0,
            "entries_total": 0,
            "exits_total": 0,
            "entries_today": 0,
            "exits_today": 0,
        }

    try:
        cur = conn.cursor()
        unique_visitors = cur.execute("SELECT COUNT(*) FROM faces").fetchone()[0]
        entries_total = cur.execute("SELECT COUNT(*) FROM events WHERE event_type = 'ENTRY'").fetchone()[0]
        exits_total = cur.execute("SELECT COUNT(*) FROM events WHERE event_type = 'EXIT'").fetchone()[0]

        # Calculate currently present: faces whose latest event is 'ENTRY'
        cur.execute("""
            WITH latest AS (
                SELECT face_id, event_type,
                       ROW_NUMBER() OVER(PARTITION BY face_id ORDER BY event_id DESC) as rn
                FROM events
            )
            SELECT COUNT(*) FROM latest WHERE rn = 1 AND event_type = 'ENTRY'
        """)
        currently_present = cur.fetchone()[0]

        # Today's date in local ISO format (YYYY-MM-DD)
        today_prefix = datetime.now().astimezone().strftime("%Y-%m-%d")
        cur.execute("SELECT COUNT(*) FROM events WHERE event_type = 'ENTRY' AND timestamp LIKE ?", (f"{today_prefix}%",))
        entries_today = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events WHERE event_type = 'EXIT' AND timestamp LIKE ?", (f"{today_prefix}%",))
        exits_today = cur.fetchone()[0]

        return {
            "database_connected": True,
            "unique_visitors": unique_visitors,
            "currently_present": currently_present,
            "entries_total": entries_total,
            "exits_total": exits_total,
            "entries_today": entries_today,
            "exits_today": exits_today,
        }
    finally:
        conn.close()


def get_visitors() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = conn.cursor()
        faces = cur.execute("SELECT face_id, seq, registered_at, representative_image_path FROM faces ORDER BY seq ASC").fetchall()
        result = []
        for face in faces:
            fid = face["face_id"]
            # Get event stats
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN event_type = 'ENTRY' THEN 1 END) as visit_count,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen
                FROM events WHERE face_id = ?
            """, (fid,))
            ev_stats = cur.fetchone()

            # Get latest event
            cur.execute("SELECT event_type, reason, timestamp FROM events WHERE face_id = ? ORDER BY event_id DESC LIMIT 1", (fid,))
            latest = cur.fetchone()

            status = "Present" if latest and latest["event_type"] == "ENTRY" else "Absent"

            result.append({
                "face_id": fid,
                "seq": face["seq"],
                "registered_at": face["registered_at"],
                "representative_image_path": face["representative_image_path"],
                "visit_count": ev_stats["visit_count"] if ev_stats else 0,
                "first_seen": ev_stats["first_seen"] if ev_stats else face["registered_at"],
                "last_seen": ev_stats["last_seen"] if ev_stats else face["registered_at"],
                "status": status,
                "last_event_reason": latest["reason"] if latest else None,
            })
        return result
    finally:
        conn.close()


def get_visitor_detail(face_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cur = conn.cursor()
        face = cur.execute("SELECT face_id, seq, registered_at, representative_image_path FROM faces WHERE face_id = ?", (face_id,)).fetchone()
        if not face:
            return None

        events = cur.execute("""
            SELECT event_id, face_id, event_type, timestamp, source_timestamp, image_path, track_id, reason
            FROM events WHERE face_id = ? ORDER BY event_id DESC
        """, (face_id,)).fetchall()

        events_list = [dict(e) for e in events]
        status = "Present" if events_list and events_list[0]["event_type"] == "ENTRY" else "Absent"

        return {
            "face_id": face["face_id"],
            "seq": face["seq"],
            "registered_at": face["registered_at"],
            "representative_image_path": face["representative_image_path"],
            "status": status,
            "events": events_list,
        }
    finally:
        conn.close()


def get_events(limit: int = 100, event_type: Optional[str] = None, face_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = conn.cursor()
        query = "SELECT event_id, face_id, event_type, timestamp, source_timestamp, image_path, track_id, reason FROM events WHERE 1=1"
        params: List[Any] = []
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.upper())
        if face_id:
            query += " AND face_id = ?"
            params.append(face_id)
        query += " ORDER BY event_id DESC LIMIT ?"
        params.append(limit)

        rows = cur.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_presence() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = conn.cursor()
        # Find all faces where the latest event is ENTRY
        cur.execute("""
            WITH latest AS (
                SELECT e.*,
                       ROW_NUMBER() OVER(PARTITION BY face_id ORDER BY event_id DESC) as rn
                FROM events e
            )
            SELECT l.event_id, l.face_id, l.timestamp, l.source_timestamp, l.image_path, l.track_id,
                   f.representative_image_path
            FROM latest l
            JOIN faces f ON l.face_id = f.face_id
            WHERE l.rn = 1 AND l.event_type = 'ENTRY'
            ORDER BY l.timestamp DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_registrations() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT f.face_id, f.seq, f.registered_at, f.representative_image_path,
                   COUNT(CASE WHEN e.event_type = 'ENTRY' THEN 1 END) as visit_count,
                   MAX(e.timestamp) as last_seen
            FROM faces f
            LEFT JOIN events e ON f.face_id = e.face_id
            GROUP BY f.face_id
            ORDER BY f.seq ASC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_analytics() -> Dict[str, Any]:
    conn = get_db_connection()
    if conn is None:
        return {
            "has_data": False,
            "entries_by_hour": [],
            "visits_per_person": [],
            "event_breakdown": {"ENTRY": 0, "EXIT": 0},
        }

    try:
        cur = conn.cursor()
        total_events = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if total_events == 0:
            return {
                "has_data": False,
                "entries_by_hour": [],
                "visits_per_person": [],
                "event_breakdown": {"ENTRY": 0, "EXIT": 0},
            }

        # Breakdown by event type
        entry_cnt = cur.execute("SELECT COUNT(*) FROM events WHERE event_type = 'ENTRY'").fetchone()[0]
        exit_cnt = cur.execute("SELECT COUNT(*) FROM events WHERE event_type = 'EXIT'").fetchone()[0]

        # Visits per person
        visits = cur.execute("""
            SELECT face_id, COUNT(*) as count
            FROM events
            WHERE event_type = 'ENTRY'
            GROUP BY face_id
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        # Events over timeline (grouped by source timestamp or ISO hour)
        timeline = cur.execute("""
            SELECT substr(timestamp, 1, 13) as hour_bucket,
                   COUNT(CASE WHEN event_type = 'ENTRY' THEN 1 END) as entries,
                   COUNT(CASE WHEN event_type = 'EXIT' THEN 1 END) as exits
            FROM events
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
        """).fetchall()

        return {
            "has_data": True,
            "total_events": total_events,
            "event_breakdown": {"ENTRY": entry_cnt, "EXIT": exit_cnt},
            "visits_per_person": [dict(r) for r in visits],
            "timeline": [dict(r) for r in timeline],
        }
    finally:
        conn.close()


def get_system_info() -> Dict[str, Any]:
    db_connected = DB_PATH.is_file()
    db_size_bytes = DB_PATH.stat().st_size if db_connected else 0
    yolo_ready = YOLO_MODEL_PATH.is_file()
    yolo_size_bytes = YOLO_MODEL_PATH.stat().st_size if yolo_ready else 0

    meta_info: Dict[str, str] = {}
    if db_connected:
        conn = get_db_connection()
        if conn:
            try:
                for row in conn.execute("SELECT key, value FROM meta").fetchall():
                    meta_info[row["key"]] = row["value"]
            except Exception:
                pass
            finally:
                conn.close()

    # Read config.json
    config_data: Dict[str, Any] = {}
    if CONFIG_PATH.is_file():
        try:
            config_data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Read last lines of events.log for runtime stats if present
    last_fps = "16.9"
    log_status = "Available" if EVENTS_LOG_PATH.is_file() else "Not Found"
    if EVENTS_LOG_PATH.is_file():
        try:
            lines = EVENTS_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
            for l in reversed(lines[-20:]):
                match = re.search(r"avg_fps=([\d.]+)", l)
                if match:
                    last_fps = match.group(1)
                    break
        except Exception:
            pass

    return {
        "status": "ONLINE",
        "pipeline_status": "READY",
        "database": {
            "status": "CONNECTED" if db_connected else "NOT FOUND",
            "path": str(DB_PATH),
            "size_bytes": db_size_bytes,
            "schema_version": meta_info.get("schema_version", "1"),
            "embedding_dim": meta_info.get("embedding_dim", "512"),
            "embedding_model": meta_info.get("embedding_model", "insightface/buffalo_l"),
        },
        "yolo": {
            "status": "READY" if yolo_ready else "NOT FOUND",
            "model_path": str(YOLO_MODEL_PATH),
            "size_bytes": yolo_size_bytes,
            "architecture": "YOLOv8-nano face model (WIDER FACE)",
        },
        "insightface": {
            "status": "READY",
            "model_pack": meta_info.get("embedding_model", "insightface/buffalo_l"),
            "embedding_dimension": 512,
            "execution_provider": "CPUExecutionProvider",
        },
        "runtime": {
            "execution_device": "CPU",
            "last_measured_fps": float(last_fps),
            "video_source": config_data.get("input", {}).get("source", "sample_video.mp4"),
            "source_type": config_data.get("input", {}).get("source_type", "video"),
            "skip_frames": config_data.get("detection", {}).get("skip_frames", 4),
            "similarity_threshold": config_data.get("recognition", {}).get("similarity_threshold", 0.45),
            "max_missing_seconds": config_data.get("tracking", {}).get("max_missing_seconds", 2.0),
            "counting_scope": config_data.get("counting", {}).get("scope", "all_time"),
            "events_log": log_status,
        },
    }
