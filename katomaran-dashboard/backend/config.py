"""Backend configuration and file paths."""
from pathlib import Path

# Paths relative to this backend module
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent.parent
TRACKER_DIR = PROJECT_ROOT / "katomaran-face-tracker"

DB_PATH = TRACKER_DIR / "data" / "faces.db"
LOGS_DIR = TRACKER_DIR / "logs"
EVENTS_LOG_PATH = LOGS_DIR / "events.log"
CONFIG_PATH = TRACKER_DIR / "config.json"
YOLO_MODEL_PATH = TRACKER_DIR / "models" / "yolov8n-face.pt"
