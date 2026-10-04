# Assumptions and decisions

Items marked **(approved)** were agreed in the Phase 1 review; the rest are decisions taken during the build because the problem statement is silent.

1. **ENTRY/EXIT meaning (approved).** ENTRY = a recognised person becomes visible; EXIT = absent longer than `tracking.max_missing_seconds`. This is presence-based, not door-line crossing.
2. **Timeout in seconds (approved).** Primary setting is `max_missing_seconds` (2.0 default); stream time is used so it behaves the same for files and live streams.
3. **Shutdown (approved).** On stop or end of file, everyone still present gets `EXIT` with `reason=shutdown`; normal departures use `person_left`.
4. **Tracker behaviour between detections (approved approach).** YOLO runs every `skip_frames+1` frames; between them tracks coast on estimated velocity. The tracker is ByteTrack-style (two-stage association) but simplified (no Kalman filter, greedy assignment).
5. **Timestamps.** `timestamp` = wall-clock local time with UTC offset when the event is recorded; `source_timestamp` = position in the video (`HH:MM:SS.mmm`), NULL for RTSP. For video files the wall time is processing time. EXIT is stamped when the exit is *confirmed*.
6. **Unique visitor count.** = number of distinct Face IDs. Default scope `all_time` = rows in `faces` (persists across restarts, includes earlier runs of the same database). Use `--db` for a fresh count, or `counting.scope = session` to count only this run.
7. **Entry delay.** An identity decision needs `embeddings_per_decision` (3) good-quality embeddings from successive detection cycles, so ENTRY is emitted slightly after the face first appears. Faces that never pass the quality gate are never registered or counted.
8. **Identity is fixed per track.** Once a track has a Face ID it is not re-verified. A new track (e.g. after a long occlusion) is resolved again from scratch.
9. **One embedding per registered face.** The registration embedding is the average of the first good embeddings. There is no gallery update.
10. **Embedding model.** InsightFace `buffalo_l` (ArcFace, 512-d); dimension is measured at runtime. Changing model requires a new database (the app refuses mixed embeddings).
11. **YOLO model.** `yolov8n-face.pt` (box only), supplied by you; path is configurable. Landmarks are obtained from InsightFace's own detector on a padded crop. If a model with 5 keypoints is used, `norm_crop` alignment is used instead automatically.
12. **Default numbers are starting points** (`confidence_threshold` 0.5, `skip_frames` 4, `similarity_threshold` 0.45, quality thresholds). They are not tuned on any video.
13. **Privacy.** Face crops and embeddings are stored locally only; `data/*.db`, `logs/*`, images, `.env`, models and videos are git-ignored; embeddings and RTSP credentials are never logged.
14. **Sample video / camera** are not available to the build; all vision-dependent behaviour is unverified until run by you.
15. **Single camera, single process.**
16. **Time zone.** Local time of the machine running the app.
