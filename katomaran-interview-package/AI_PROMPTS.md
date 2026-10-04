# AI prompts (actual prompts only)

Nothing here is invented. These are the prompts that were really sent in the build conversation. The original prompts are long; the originals are in your saved prompt files. Paste them below if you need verbatim copies.

## Prompt 1 - Phase 1 (requirements and architecture)
Role: "senior Python computer-vision engineer, AI architect, and hackathon mentor". Asked for an incremental, modular build of "Intelligent Face Tracker with Auto-Registration and Visitor Counting" with 35 hackathon requirements, preferred stack (OpenCV, Ultralytics YOLO, InsightFace, ByteTrack, SQLite, logging, JSON config), the pipeline diagram, Track ID vs Face ID vs Detection distinction, entry/exit state machine, DB schema, tests A-H, 12 development phases, "Interview Explanation" per module, a "DO NOT DO THESE THINGS" list and acceptance criteria. Final instruction: "Do NOT write implementation code yet. Start with PHASE 1 only ... Then STOP."

Full text: *paste from your file*

## Prompt 2 - Full build
"KATOMARAN INTELLIGENT FACE TRACKER - FULL APPLICATION BUILD - PHASE 2": Phase 1 approved; build the complete application in a single pass; two separate directories (`katomaran-face-tracker/`, `katomaran-interview-package/`); use seconds-based `max_missing_seconds`; EXIT with `reason=shutdown`; `app/event_logging/`; store wall-clock and source timestamps; face-specific YOLO model verified for compatibility/licence; embedding dimension from the model; do not fabricate results; mark `NOT VERIFIED`; final requirement matrix; interview package of 16 named files based on the actual code.

Full text: *paste from your file*

## Prompt 3
"go now" (proceed).

## Prompt 4
"continue" (continue the build after documentation of the application was complete).

## Good prompts for your own follow-up work in Antigravity
These are suggestions, not prompts that were used:
- "Run `python -m pytest -q`, then run the app on `sample_video.mp4 --no-display --max-frames 200` and fix any import or model-loading error without changing behaviour."
- "Add a debug overlay showing the cosine similarity of each track to its assigned Face ID."
- "Implement periodic re-verification of resolved tracks every N seconds and log `IDENTITY_CHANGED` if the match differs."
