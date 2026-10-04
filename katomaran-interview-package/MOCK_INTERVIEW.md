# Mock interview (answers reflect the actual implementation)

**1. Introduce the project.** See 1-minute explanation in `PROJECT_OVERVIEW.md`.

**2. Walk me through the architecture.** Source -> scheduler -> YOLO -> tracker -> identity resolver (quality, embedding x3, average) -> registry (cosine vs gallery) -> presence state machine -> recorder (image, SQLite, `events.log`) -> counter. Pipeline is orchestration only; everything is injected.

**3. Why YOLO and which model?** Brief requires YOLO. A face-trained model is needed: `yolov8n-face.pt` (WIDER FACE), nano for speed, box-only. Ultralytics is AGPL, model repo GPL - fine for a prototype, check for commercial use.

**4. How does tracking work and how does frame skipping affect it?** Two-stage IoU association (high then low confidence); on skipped frames boxes coast using velocity. Fewer detections = less compute, more drift/missed short appearances. Interval must stay below `max_missing_seconds`.

**5. Track ID vs Face ID?** Track ID is temporary and can change; Face ID is permanent from embedding match. Presence is keyed by Face ID.

**6. How do you decide new vs existing person?** Average 3 good normalised embeddings, cosine similarity to every stored embedding, `>= 0.45` (starting value, calibrated) -> existing; else create F00N in the DB.

**7. How did you choose 0.45?** I didn't claim it's optimal; it's a configurable starting value in the usual range for ArcFace cosine similarity. I calibrate with same-person vs different-person similarity distributions on the actual video. *(Say what you measured.)*

**8. How do you guarantee one ENTRY and one EXIT?** ENTRY only on ABSENT->PRESENT; EXIT only on MISSING timeout or shutdown, after which the session is deleted. Tests A-H prove it.

**9. What if a person is hidden for a second?** State goes MISSING, no event; returns before 2 s -> PRESENT again silently.

**10. What happens on restart?** Gallery is rebuilt from the `faces` table; IDs continue from `MAX(seq)`; embedding model/dimension checked.

**11. Database design and why SQLite?** `faces`, `events`, `meta`; images on disk, paths in DB; WAL, transactions, constraints. SQLite fits a single-process prototype; PostgreSQL for multi-camera.

**12. RTSP specifics?** Reader thread, newest frame only, reconnect with limit, credentials via `.env` and redacted in logs. Not yet verified against my real camera *(update after testing)*.

**13. Debug scenario: duplicate IDs for one person.** Read `FACE_REGISTERED ... closest_existing_similarity`; if just below threshold, calibrate/raise quality; check crops in `logs/registrations/`.

**14. Performance?** Quote only measured numbers from the metrics block. Design: skipping, per-track embedding caching, no per-frame I/O, GPU fallback.

**15. AI-assisted coding?** Planned in phases with review, generated in one pass, validated by tests and my own runs; explain limitations honestly.

**16. Limitations?** Simplified tracker, no re-verification, single embedding per person, no liveness, presence-based ENTRY/EXIT, unverified real-model accuracy until calibrated.

**17. Future improvements?** See `HR_AND_PROJECT_QUESTIONS.md`.

**18. Ownership.** "I can modify any module live: e.g. change the timeout, add a column to `events`, or swap the tracker via the `predict/update` interface."
