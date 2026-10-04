# Tracking concepts

## Why track at all?
Detection gives independent boxes per frame. Tracking says "this box is the same face as that box a moment ago", so we recognise once per track instead of every frame, and bridge frames where YOLO did not run or missed.

## ByteTrack idea
Most trackers throw away low-confidence detections. ByteTrack keeps them: first match high-confidence boxes to tracks, then try to match the *remaining tracks* with low-confidence boxes (often a partly hidden face). That reduces lost tracks and ID switches.

## What our `ByteTracker` does
1. `predict()` every frame: move each box by its velocity, decay velocity (x0.85).
2. On detection frames `update()`: stage 1 high-confidence (>= 0.5) vs tracks, IoU >= 0.3, greedy by highest IoU; stage 2 low-confidence (0.2-0.5) vs leftover tracks, IoU >= 0.5; unmatched high-confidence detections become new tracks.
3. A track unmatched for more than `track_buffer_seconds` (2.0) is removed (`TRACK_LOST`). Track IDs are never reused.

## Differences from real ByteTrack
Kalman filter -> damped constant velocity; Hungarian assignment -> greedy; no ReID features. Swappable: the pipeline only uses `predict()` and `update()`.

## Frame skipping and tracking
YOLO every `skip_frames+1` frames; in between the box is a *prediction*. Predictions are not evidence of presence: only tracks matched to a fresh detection (`matched_this_update`) feed identity and presence.

## Track ID vs Face ID
Track ID 17 may become 23 for the same person after occlusion. Face ID F003 stays. Presence uses Face ID. The log line `ENTRY | face_id=F001 track_id=3` after an earlier `track_id=1` is the proof (see sample in project `docs/TESTING.md`).

## Failure cases
Crossing people can swap IDs; fast motion with large skip intervals drifts; crowded scenes exceed greedy matching quality; very long occlusion starts a new track that must be re-recognised.
