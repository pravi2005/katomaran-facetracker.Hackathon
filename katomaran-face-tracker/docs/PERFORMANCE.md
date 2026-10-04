# Performance and CPU/GPU considerations

**No FPS or accuracy number is claimed anywhere in this project.** Run the application and read the measured block printed at exit (`frames`, `avg_fps`, and per-stage `read`, `detect`, `recognise`, `presence_expire` timings). `--no-display --max-frames N` gives a repeatable benchmark.

## Where the compute goes

| Stage | Runs | Cost driver | Device |
|---|---|---|---|
| Video decode | every frame | resolution/codec | CPU |
| YOLO face detection | every `skip_frames+1` frames | model size, `detection.image_size` | GPU if available (`detection.device`) else CPU |
| Tracker predict/update | every frame / detection frames | number of faces (tiny NumPy work) | CPU |
| Quality gate | detection frames, unresolved tracks | one resize + Laplacian | CPU |
| InsightFace embedding | only unresolved tracks (about `embeddings_per_decision` times per track) | ResNet50 ArcFace, plus SCRFD on the padded crop (no landmarks from YOLO) | ONNX Runtime CUDA if `onnxruntime-gpu` + CUDA, else CPU |
| Matching | when an identity decision is made | gallery size (matrix product) | CPU |
| SQLite / images / log | only on registrations and ENTRY/EXIT events | tiny | disk |

## Built-in optimisations

- Detection frame skipping (configurable); tracker coasts in between.
- **Embedding caching per track:** once a track has a Face ID no further embeddings are computed for it.
- Averaging 3 embeddings (configurable) instead of re-embedding every frame.
- No per-frame DB writes or logging; WAL journal; events only.
- RTSP reader thread keeps only the newest frame, so a slow pipeline does not accumulate lag.
- GPU auto-detection with CPU fallback for both YOLO (PyTorch) and InsightFace (ONNX Runtime).

## Tuning guide

| Goal | Change | Trade-off |
|---|---|---|
| Faster | raise `detection.skip_frames`; lower `detection.image_size`; use a GPU | more drift between detections, small faces missed |
| More robust tracking | lower `skip_frames` | more compute |
| Fewer duplicate IDs | better quality gate (`min_face_size_px`, `blur_threshold`), more `embeddings_per_decision`, calibrated threshold | slower ENTRY |
| Fewer false EXITs | raise `tracking.max_missing_seconds` | slower EXIT |

Constraint: `(skip_frames + 1) / fps` must be smaller than `max_missing_seconds` (the pipeline logs `CONFIG_WARNING` otherwise).

## Threshold calibration (recognition accuracy)

1. Collect crops from `logs/entries/` of several people (sorted by hand into `calibration_faces/<person>/`).
2. `python scripts/calibrate_threshold.py calibration_faces`.
3. The script prints the 5th percentile of same-person similarity and the 95th percentile of different-person similarity. If they separate, the midpoint is a sensible threshold; if they overlap, no threshold is clean for that data (improve crop quality).
4. Put the value into `recognition.similarity_threshold`. Re-test with the whole video. (Script **NOT VERIFIED** with the real model; the maths is unit-tested.)

## Scalability notes

Gallery search is a brute-force NumPy matrix product (fine for hundreds to low thousands of faces); beyond that use FAISS or an ANN index. One process handles one camera; several cameras would need one process each (SQLite WAL tolerates this for reads, writes are serialised) or a different database.
