# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: YOLO model file not found ...` | model not downloaded | Put a YOLO **face** model at `models/yolov8n-face.pt` or edit `detection.model` |
| `The 'ultralytics' package is not installed` | requirements not installed in the active venv | `pip install -r requirements.txt` |
| `pip install insightface` fails with "Failed building wheel" (Windows) | PyPI ships source only; needs a C++ compiler | Install Microsoft C++ Build Tools ("Desktop development with C++"), or use a prebuilt wheel that matches your Python version (only from a source you trust), then re-run pip |
| `numpy` / `opencv` import or ABI errors | numpy 2.x vs packages built for numpy 1.x | `pip install "numpy<2"` and reinstall opencv/insightface |
| InsightFace cannot download `buffalo_l` | no internet / proxy | Download the model pack manually into `~/.insightface/models/buffalo_l/` |
| `onnxruntime` GPU not used | both `onnxruntime` and `onnxruntime-gpu` installed, or CUDA/cuDNN mismatch | Uninstall both, install only `onnxruntime-gpu` matching your CUDA version; run `python -c "import onnxruntime as o; print(o.get_available_providers())"` and look for `CUDAExecutionProvider` |
| YOLO runs on CPU although you have a GPU | CPU-only PyTorch | Install the CUDA build of PyTorch from pytorch.org; `python -c "import torch; print(torch.cuda.is_available())"` |
| `ERROR: Video file not found` | wrong path (relative paths are resolved against the folder containing `config.json`) | use an absolute path or `--source` |
| `OpenCV cannot open video` | unsupported codec / corrupt file | re-encode with ffmpeg: `ffmpeg -i in.mp4 -c:v libx264 out.mp4` |
| `RTSP_ERROR connect_failed` | wrong URL, credentials, network/firewall, camera busy | test the URL in VLC; check `.env`; app retries `input.reconnect_max_attempts` times |
| RTSP video lags behind real time | slow processing | raise `skip_frames`, lower `image_size`, use GPU (the reader already drops stale frames) |
| `cv2.imshow` error / no window | `opencv-python-headless` installed or no display | `pip uninstall opencv-python-headless && pip install opencv-python`, or use `--no-display` |
| `IncompatibleEmbeddingError` | database made with another model | use a new `--db` path (embeddings from different models are not comparable) |
| One person gets several Face IDs | threshold too high / poor crops | calibrate threshold, raise `min_face_size_px` / `blur_threshold`, raise `embeddings_per_decision` |
| Two people share one Face ID | threshold too low | raise `similarity_threshold`, recalibrate |
| Face never registered, stays `UNKNOWN` | crops rejected by the quality gate | lower `blur_threshold` / `min_face_size_px`, check lighting; `max_resolve_attempts` reached logs `RECOGNITION_FAILED` |
| Unexpected EXIT while person is in view | `max_missing_seconds` too small, or detection interval too long | raise `max_missing_seconds` or lower `skip_frames` (see `CONFIG_WARNING`) |
| Count includes people from earlier runs | `counting.scope = all_time` with an old database | use `--db data/new.db`, or `counting.scope = session` |
| `DATABASE_ERROR ... database is locked` | another process (e.g. DB viewer) holds a write lock | close it; events are queued and retried automatically |
| Permission errors writing `logs/` or `data/` | folder permissions | choose writable paths in `config.json` |
