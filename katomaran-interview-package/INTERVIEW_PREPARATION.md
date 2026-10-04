# Interview preparation plan

## Before the interview (do these, in this order)
1. Install and run once on your machine: `python -m pytest -q` (expect 93 passed), then run the app on the sample video with `--db data/demo.db` and fix any install problem (see project `docs/TROUBLESHOOTING.md`).
2. Watch the first minutes of the video: does each person get one Face ID? If not, calibrate the threshold (`scripts/calibrate_threshold.py`) and write down the final value and what you observed. **Replace the defaults in your answers with your measured findings.**
3. Capture real evidence for the README/demo: `events.log` excerpt, one registration image, and the SQL queries output.
4. Test RTSP with the actual camera URL in `.env` the day before. Note latency and reconnect behaviour.
5. Read `QUICK_REVISION.md` the evening before and `MOCK_INTERVIEW.md` aloud.

## Suggested live-demo script (5 minutes)
1. Show the architecture diagram (README) and name the four concepts: detection, Track ID, Face ID, presence state.
2. Run with the video; point at UNKNOWN (orange) turning into F001 (green) after about three detection cycles, and explain why (embedding averaging).
3. Open `events.log`: `FACE_REGISTERED`, `ENTRY`, `EXIT ... reason=person_left`.
4. Run the SQL: `SELECT COUNT(*) FROM faces;` vs. events table; show the same Face ID re-entering with a new Track ID.
5. Change `skip_frames` in `config.json` and explain the trade-off.
6. Show tests: scenarios A-H in `tests/test_pipeline_scenarios.py`.

## Being honest about AI-assisted development
Say: "I used an AI assistant to plan and generate the code in stages, reviewed the architecture myself, and made decisions such as seconds-based timeouts and EXIT-on-shutdown. I can explain every module; the part I verified myself is X, and the thing I'm still calibrating is the recognition threshold." Only claim what you actually did. Be ready to modify code live (e.g. change the timeout, add a column).

## Things interviewers commonly probe in this project
- Why not make a new ID for each detection? (count would explode)
- How do you stop duplicate ENTRY events? (state machine keyed by Face ID)
- What if the same person looks different/occluded? (averaging, quality gate, threshold, limits)
- What happens if the database or camera fails? (retry queue, reconnect, errors logged)
- How would you scale to many cameras / thousands of people? (FAISS, per-camera workers, Postgres)
- Privacy of face data. (local storage, git-ignored, never log embeddings, consent/retention)
