# Katomaran Web Dashboard

A modern, responsive dark-themed web dashboard for visual monitoring and analysis of the Katomaran Face Tracking and Auto-Registration AI application.

---

## 1. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Web Browser                             │
│       React + Vite + Tailwind CSS + Lucide Icons             │
└──────────────────────────────▲───────────────────────────────┘
                               │ HTTP / REST (Read-Only)
┌──────────────────────────────▼───────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│    Reads data directly from SQLite & local logs/images       │
└───────────────▲──────────────────────────────▲───────────────┘
                │                              │
┌───────────────▼──────────────┐┌──────────────▼───────────────┐
│      SQLite Database         ││      Image Store & Logs      │
│  data/faces.db (Read-Only)   ││  logs/ (entries, exits, ...) │
└──────────────────────────────┘└──────────────────────────────┘
```

The dashboard operates as a **non-invasive, read-only observer** on top of the Katomaran Face Tracker. It connects directly to the existing SQLite database (`data/faces.db`), reads stored event images (`logs/`), and parses runtime telemetry from `logs/events.log` without requiring changes to the core AI pipeline.

---

## 2. Dashboard Pages

| Page | Description |
|---|---|
| **Dashboard** | Overview cards (Currently Present, Unique Visitors, Entries Today, Exits Today), pipeline model status indicators, live presence list, and recent events feed. |
| **Live Camera** | Video monitoring interface with HUD telemetry (FPS, Active Tracks, Present Count) and clear status indicators for standalone AI video processing. |
| **Visitors** | Searchable table of registered identities (`F001`, `F002`, ...), status badges (Present/Absent), first/last seen timestamps, visit frequency, and detail modal. |
| **Events** | Full audit timeline of `ENTRY` and `EXIT` events with source video timestamps, exit reasons (`person_left`, `shutdown`), track IDs, and face crop images. Filter by event type and search by Face ID. |
| **Analytics** | Visual charts showing transition distribution (Entries vs Exits) and top visitor frequencies. |
| **Registered Faces** | Card gallery displaying all stored identity portraits, sequence numbers, registration dates, and links to full presence history. |
| **System** | Diagnostic cards displaying YOLOv8n detector status, InsightFace ArcFace model pack (512-d), ONNX Runtime execution provider (CPU), measured processing FPS (~16.9 FPS), and `config.json` parameters. |

---

## 3. API Endpoints

All endpoints are strictly **READ-ONLY**:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status. |
| `GET` | `/api/stats` | Real-time counts (present, unique visitors, entries/exits today and total). |
| `GET` | `/api/visitors` | All recognized identities with visit counts and presence state. |
| `GET` | `/api/visitors/{face_id}` | Detailed presence timeline and images for a specific visitor. |
| `GET` | `/api/events` | Event log table with optional filters (`?event_type=ENTRY&face_id=F001&limit=100`). |
| `GET` | `/api/presence` | List of visitors currently inside the camera view. |
| `GET` | `/api/registrations` | Registered faces with metadata and gallery portraits. |
| `GET` | `/api/analytics` | Transition ratios and visit distributions. |
| `GET` | `/api/system` | Model versions, database file size, execution provider, and measured FPS. |
| `GET` | `/api/live/status` | Connection state of the live camera stream. |
| `GET` | `/api/images/{path}` | Safely serves cropped face JPEG images from `logs/`. |

---

## 4. Setup and How to Run

### Option A: All-in-One Fast Mode (FastAPI serves built React SPA)

The React frontend has been pre-built into `frontend/dist`. You can run the entire dashboard using just Python:

```bash
cd katomaran-dashboard/backend
python main.py
```

Then open your browser at:
`http://localhost:8000`

---

### Option B: Development Mode (Vite + FastAPI Hot-Reload)

#### 1. Start the Backend:
```bash
cd katomaran-dashboard/backend
python main.py
# Backend runs at http://localhost:8000
```

#### 2. Start the Frontend:
```bash
cd katomaran-dashboard/frontend
npm install   # (if not already installed)
npm run dev
# Vite dev server runs at http://localhost:3000
```

Open `http://localhost:3000` in your browser. Vite automatically proxies `/api` calls to `http://localhost:8000`.

---

## 5. Database Connection

The dashboard backend connects to `../katomaran-face-tracker/data/faces.db` using SQLite's read-only URI mode:

```python
sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)
```

- **Safety:** Zero write operations are executed by the dashboard.
- **Concurrency:** Uses SQLite WAL mode to query concurrently while the AI tracker processes video frames.

---

## 6. Live Camera Interface & Limitations

- The Katomaran AI pipeline currently runs as a standalone Python vision process, rendering its real-time bounding boxes (green/orange) via an OpenCV desktop window.
- The web dashboard provides the camera monitor viewport and HUD telemetry.
- Direct WebRTC/MJPEG browser streaming requires an RTSP gateway or an MJPEG frame-broadcasting thread in a future integration step. The Live Camera page clearly indicates this state.

---

## 7. Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `Stats showing 0 or database not found` | The AI pipeline has not been run yet to generate `faces.db`. | Run `python -m app.main --source sample_video.mp4` in `katomaran-face-tracker/`. |
| `Images not loading` | Relative image paths not found in `logs/`. | Ensure `logs/` directory contains `entries/`, `exits/`, and `registrations/`. |
| `Port 8000 already in use` | Another process is using port 8000. | Change port in `main.py` or run `uvicorn main:app --port 8001`. |
