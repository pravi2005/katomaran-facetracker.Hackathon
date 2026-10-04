# AI planning document

## 1. Problem analysis

The Katomaran problem statement asks for a face tracker with auto-registration, recognition, ENTRY/EXIT events, evidence images, a database, `events.log` and an accurate **unique** visitor count. The hard parts are not the models but the **correctness rules**:
- one person must never become two identities (or two people one) -> embedding quality + threshold calibration;
- one visit must produce exactly one ENTRY and one EXIT -> a state machine independent of detector flicker;
- state must survive restarts -> database-generated IDs, persisted embeddings.

Requirements were split into *mandatory* (the 35 numbered items of the brief) and *optional enhancements* (quality gate, embedding averaging, calibration script, session count scope) and the optional ones are labelled as such in the docs.

## 2. Architecture decisions (reviewed in Phase 1, then built)

| Decision | Reason | Trade-off |
|---|---|---|
| Presence keyed by Face ID, not Track ID | Tracker IDs switch after occlusion | needs identity before ENTRY (small delay) |
| Time-based timeout (`max_missing_seconds`) | frame counts mean different durations for files vs RTSP | needs a stream clock |
| Video files use video time for timeouts | results do not depend on processing speed | wall time still stored separately |
| Averaged embeddings (3) + quality gate | one bad frame must not create a person | ENTRY delayed ~3 detection cycles |
| Own ByteTrack-style tracker | no extra dependency, fully unit-testable, tracker API is swappable | simplified motion model, greedy matching |
| SQLite + files | brief asks for DB + local images; single-process prototype | not for multi-camera scale |
| Dependency injection in `Pipeline` | tests run with fakes (no GPU/models) | one extra composition file |
| `app/event_logging/` instead of `app/logging/` | avoids shadowing the stdlib `logging` module | none |

## 3. AI-assisted development workflow

1. Prompt 1: ask the AI for **analysis and architecture only** (Phase 1) and stop for human review.
2. Human review of the architecture, ambiguities and questions; decisions recorded (timeouts in seconds, shutdown EXIT, timestamps, renamed logging package).
3. Prompt 2: build the whole application in one pass, including tests, docs and a separate interview package.
4. The AI verified model/library facts by web search (face-model repository, licences, InsightFace installation issues) and recorded what stayed unverified.
5. Code was written module by module, tests were run after the core was in place, and docs were written **after** the code so they describe what exists.
6. Further debugging/modification is planned in Antigravity (see "Next steps" in the final report).

## 4. Prompts used (actual)

Only prompts that were actually sent are listed. Paste the complete original texts here before submission if the hackathon requires verbatim prompts.

| # | Prompt (summary of the user's own words) | Full text |
|---|---|---|
| 1 | "ROLE: senior Python computer-vision engineer ... build 'Intelligent Face Tracker with Auto-Registration and Visitor Counting' ... Start with PHASE 1 only ... Then STOP." (requirements, stack, architecture, state machine, DB, testing, 12 phases) | *paste original* |
| 2 | "KATOMARAN INTELLIGENT FACE TRACKER - FULL APPLICATION BUILD - PHASE 2 ... Build the complete project now ... two separate deliverables: application and interview package ... DO NOT FABRICATE" | *paste original* |
| 3 | "go now" (confirmation to proceed) | n/a |

## 5. Technology selection

| Need | Chosen | Alternatives | Why |
|---|---|---|---|
| Detection | Ultralytics YOLO + `yolov8n-face.pt` | SCRFD / RetinaFace, YOLOv8-face with landmarks | brief requires YOLO; face-trained, small; loads with stock library. AGPL/GPL licence noted |
| Recognition | InsightFace `buffalo_l` (ArcFace) | other ArcFace/AdaFace models | brief names InsightFace/ArcFace; 512-d embeddings; ONNX Runtime CPU/GPU |
| Tracking | ByteTrack-style (own) | Ultralytics BYTETracker, BoT-SORT, DeepSORT | simple, testable, appearance-free; swappable |
| DB | `sqlite3` | SQLAlchemy, PostgreSQL | no extra dependency, enough for one process |
| Matching | NumPy dot product | FAISS | brute force is exact and fine at this scale |
| Config | JSON + dataclasses + validation | pydantic | no dependency, clear errors |

## 6. Testing strategy

Pure logic tested with fakes (93 tests); model/camera behaviour documented as an integration checklist; nothing fabricated. See `TESTING.md`.

## 7. Limitations

See README section 17 and `ASSUMPTIONS.md`. Biggest open risks: threshold calibration on real video, tracker ID switches between crossing people, real RTSP behaviour, installation of InsightFace/ONNX Runtime on the demo machine.
