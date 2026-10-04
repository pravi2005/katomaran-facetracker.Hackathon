"""FastAPI backend for Katomaran Face Tracking Dashboard."""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from config import LOGS_DIR
import database as db
import analyze as az

app = FastAPI(
    title="Katomaran Face Intelligence API",
    description="Read-only monitoring API for Katomaran Face Tracker",
    version="1.0.0",
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def get_health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "katomaran-dashboard-api",
        "version": "1.0.0",
    }


@app.get("/api/stats")
def get_stats():
    """Real-time summary statistics from SQLite."""
    return db.get_stats()


@app.get("/api/visitors")
def get_visitors():
    """List of all visitors with visit counts and status."""
    return db.get_visitors()


@app.get("/api/visitors/{face_id}")
def get_visitor_detail(face_id: str):
    """Detailed event history for a specific visitor."""
    visitor = db.get_visitor_detail(face_id)
    if not visitor:
        raise HTTPException(status_code=404, detail=f"Visitor {face_id} not found")
    return visitor


@app.get("/api/events")
def get_events(
    limit: int = Query(default=100, ge=1, le=500),
    event_type: Optional[str] = Query(default=None, regex="^(ENTRY|EXIT)$"),
    face_id: Optional[str] = None,
):
    """Event timeline from SQLite with filtering."""
    return db.get_events(limit=limit, event_type=event_type, face_id=face_id)


@app.get("/api/presence")
def get_presence():
    """Currently present visitors."""
    return db.get_presence()


@app.get("/api/registrations")
def get_registrations():
    """Registered faces and metadata."""
    return db.get_registrations()


@app.get("/api/analytics")
def get_analytics():
    """Aggregated timeline and visit distributions."""
    return db.get_analytics()


@app.get("/api/system")
def get_system():
    """System, model, database, and pipeline operational status."""
    return db.get_system_info()


@app.get("/api/live/status")
def get_live_status():
    """Check live camera / stream connection state."""
    # The existing application processes videos batch-wise or displays via local cv2 window.
    # It does not host an MJPEG/WebRTC server yet.
    return {
        "stream_connected": False,
        "mode": "standalone_ai_pipeline",
        "message": "Live WebRTC/MJPEG video stream not connected. The AI pipeline runs locally in terminal/GUI window.",
    }


@app.get("/api/images/{image_path:path}")
def get_image(image_path: str):
    """Safely serve cropped face images from logs directory."""
    # Prevent directory traversal
    clean_path = Path(image_path).as_posix().lstrip("/\\")
    full_path = (LOGS_DIR / clean_path).resolve()

    if not str(full_path).startswith(str(LOGS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(full_path, media_type="image/jpeg")



# ---------------------------------------------------------------------------
# Video Analysis Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
async def upload_and_analyze(file: UploadFile = File(...)):
    """Accept a video upload and start analysis via the existing AI pipeline."""
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in az.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: {', '.join(az.ALLOWED_EXTENSIONS)}",
        )

    # Save upload to controlled directory
    az.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "upload").name  # strip any path traversal
    import uuid as _uuid
    uid = str(_uuid.uuid4())[:8]
    upload_path = az.UPLOADS_DIR / f"{uid}_{safe_name}"

    try:
        contents = await file.read()
        if len(contents) > az.MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 2 GB).")
        upload_path.write_bytes(contents)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    # Create analysis record
    rec = az.create_analysis(safe_name, upload_path)

    # Run in background thread so the request returns quickly
    def _run():
        az.run_analysis(rec)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {
        "analysis_id": rec.analysis_id,
        "filename": rec.filename,
        "status": rec.status,
        "message": "Analysis started. Poll /api/analyze/{analysis_id} for status.",
    }


@app.get("/api/analyze")
def list_analyses():
    """List all analysis sessions."""
    return [
        {
            "analysis_id": r.analysis_id,
            "filename": r.filename,
            "status": r.status,
            "created_at": r.created_at,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "error": r.error,
        }
        for r in az.list_analyses()
    ]


@app.get("/api/analyze/{analysis_id}")
def get_analysis_status(analysis_id: str):
    """Get status of a specific analysis."""
    rec = az.get_analysis(analysis_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found.")
    return {
        "analysis_id": rec.analysis_id,
        "filename": rec.filename,
        "status": rec.status,
        "created_at": rec.created_at,
        "started_at": rec.started_at,
        "finished_at": rec.finished_at,
        "error": rec.error,
        "metrics": rec.metrics,
    }


@app.get("/api/analyze/{analysis_id}/report")
def get_analysis_report(analysis_id: str):
    """Get the full analysis report once processing is complete."""
    rec = az.get_analysis(analysis_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found.")
    if rec.status == "running" or rec.status == "pending":
        return {"analysis_id": analysis_id, "status": rec.status, "message": "Still processing."}
    return az.get_report(rec)


# Mount built frontend SPA if available
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_candidate = FRONTEND_DIST / full_path
        if file_candidate.is_file():
            return FileResponse(file_candidate)
        return FileResponse(FRONTEND_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
