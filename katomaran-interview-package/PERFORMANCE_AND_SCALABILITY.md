# Performance and scalability

**Never quote an FPS number you have not measured.** Run `python -m app.main --source sample.mp4 --no-display --max-frames 300` on your machine and read the printed block; quote *that*, with your hardware.

## Where time goes (by design)
- YOLO: only every `skip_frames+1` frames (GPU if PyTorch sees CUDA).
- InsightFace embedding: only for tracks without a Face ID, about 3 times per new track. Resolved tracks cost nothing.
- Tracker/matching/presence: tiny NumPy work.
- Disk/DB: only on registrations and ENTRY/EXIT events (no per-frame writes, no per-frame logging).
- RTSP: reader thread keeps only the newest frame, so slow processing means dropped frames, not growing delay.

## Knobs
| Want | Change | Cost |
|---|---|---|
| faster | higher `skip_frames`, lower `image_size`, GPU | drift, missed small faces |
| steadier tracking | lower `skip_frames` | compute |
| fewer duplicate IDs | stricter quality, more embeddings, calibrated threshold | later ENTRY |
| fewer false EXITs | higher `max_missing_seconds` | later EXIT |

## Scalability answers
- **More people:** gallery search is a NumPy matrix product - exact and fast to thousands; beyond that use FAISS/ANN.
- **More cameras:** one process (or container) per camera; shared database must move from SQLite to PostgreSQL; embeddings could live in a vector DB; add camera ID to events.
- **Cross-camera identity:** same gallery, similarity threshold must be recalibrated per camera.
- **Throughput:** batch embeddings, TensorRT/ONNX GPU providers, smaller detector, lower resolution input.
- **Reliability:** supervisor/restart, health checks, log rotation, retention policy for images, queue (e.g. Redis/Kafka) between processing and storage.
- **Privacy at scale:** encryption at rest, retention limits, consent, access control.
