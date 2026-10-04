# Troubleshooting Q&A (what you'd say, and where to look)

**One person gets F001 and F002.** Threshold too high or poor crops. Check `events.log` `FACE_REGISTERED ... closest_existing_similarity=` for the second registration: if it is just under the threshold, calibrate; also raise quality thresholds or `embeddings_per_decision`.

**Two people share one Face ID.** Threshold too low; look at `FACE_RECOGNIZED ... similarity=`. Raise threshold, recalibrate.

**Face stays UNKNOWN (orange).** The quality gate rejects the crops (small, blurry, edge) or `max_resolve_attempts` was reached (`RECOGNITION_FAILED`). Lower `blur_threshold`/`min_face_size_px` or improve lighting.

**ENTRY arrives late.** By design 3 good embeddings are needed (3 detection cycles). Lower `embeddings_per_decision` to 1-2 at the cost of stability.

**EXIT happens while the person is visible.** `max_missing_seconds` shorter than the detection gap, or YOLO missing the face. Check `CONFIG_WARNING`; lower `skip_frames` or raise the timeout/confidence tuning.

**Unique count too high.** Duplicates (see above), or an old database (`all_time` scope). Use `--db` for a fresh DB.

**`ModelLoadError`.** YOLO file path wrong or InsightFace not installed/downloaded. Message says which.

**`pip install insightface` fails on Windows.** PyPI ships source only; install C++ Build Tools or a matching prebuilt wheel from a source you trust. Also keep `numpy<2` and install only one of `onnxruntime`/`onnxruntime-gpu`.

**GPU not used.** `python -c "import torch;print(torch.cuda.is_available())"` and `onnxruntime.get_available_providers()`.

**RTSP won't connect / drops.** Test URL in VLC; check `.env`; see `RTSP_ERROR` lines (`connect_failed`, `stream_lost`, `reconnected`); the app retries then raises `SourceError`.

**`DATABASE_ERROR`.** Locked or read-only DB; the event is queued and retried. Close other tools holding the file.

**No preview window.** `opencv-python-headless` installed or no display; use `opencv-python` or `--no-display`.

**Debug method to describe in the interview:** reproduce on the video with `--no-display`, read `events.log` around the failure (every decision is logged with track_id/face_id), check the DB rows, then adjust one config value at a time. Unit tests with fakes isolate whether the bug is in logic or in the model.
