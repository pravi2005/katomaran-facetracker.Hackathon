# ENTRY / EXIT logic (`app/presence/presence_manager.py`)

## State machine (per Face ID)
```
ABSENT --(observed)--------------------------> PRESENT   emit ENTRY
PRESENT --(not observed in a detection cycle)-> MISSING   (no event)
MISSING --(observed before timeout)-----------> PRESENT   (no event)
MISSING --(gap > max_missing_seconds)---------> ABSENT    emit EXIT (person_left)
PRESENT|MISSING --(shutdown)------------------> ABSENT    emit EXIT (shutdown)
```

## Why it can't duplicate events
ENTRY is emitted only in the branch where no session exists for the Face ID. EXIT is emitted only when a MISSING session passes the timeout (or on shutdown) and the session is deleted at the same moment. There is no other code path that emits either event.

## Walk-through (default 2.0 s timeout)
| Time | What happens | State | Event |
|---|---|---|---|
| 0.0 s | F001 resolved | ABSENT -> PRESENT | ENTRY |
| 0.2-4.0 s | visible every cycle | PRESENT | none |
| 4.2 s | not detected | MISSING | none |
| 5.0 s | back (maybe new Track ID) | PRESENT | none |
| 8.0 s | not detected | MISSING | none |
| 10.1 s | still gone, gap > 2.0 s | ABSENT | EXIT (person_left) |
| 30 s | F001 returns | ABSENT -> PRESENT | ENTRY (same Face ID, count unchanged) |

## Detail questions
- **Why `update()` and `expire()` separate?** `update()` runs on detection cycles (needs observations); `expire()` runs every frame so EXIT time is precise.
- **Which clock?** `FrameTime.stream_seconds`: video time for files (reproducible, independent of processing speed), wall time for RTSP.
- **Why Face ID key?** After an occlusion the tracker may give a new Track ID; same person, same session.
- **Two tracks, same person at once?** `update()` keeps the one with the higher confidence, so only one ENTRY.
- **EXIT image?** The last crop seen is kept in the session and saved on exit.
- **Danger:** the detection interval `(skip_frames+1)/fps` must be below `max_missing_seconds`; the pipeline logs `CONFIG_WARNING` otherwise.
- **ENTRY delay:** an ENTRY can only happen after identity resolution (3 good embeddings), so it appears roughly three detection cycles after the first appearance.
- **Tests:** `tests/test_presence_manager.py` (unit) and scenarios A-H in `tests/test_pipeline_scenarios.py` (end to end).
