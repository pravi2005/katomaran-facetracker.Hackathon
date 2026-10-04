"""Small runtime metrics: rolling FPS + per-stage wall time.

Everything printed comes from real measurements made during the run - nothing
is estimated or pre-filled.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import contextmanager
from typing import Deque, Dict, Iterator

FPS_WINDOW = 30


class Metrics:
    def __init__(self) -> None:
        self._stamps: Deque[float] = deque(maxlen=FPS_WINDOW)
        self._stage_total: Dict[str, float] = defaultdict(float)
        self._stage_calls: Dict[str, int] = defaultdict(int)
        self.frames = 0
        self.started = time.perf_counter()

    def tick(self) -> None:
        self._stamps.append(time.perf_counter())
        self.frames += 1

    @property
    def fps(self) -> float:
        if len(self._stamps) < 2:
            return 0.0
        span = self._stamps[-1] - self._stamps[0]
        return (len(self._stamps) - 1) / span if span > 0 else 0.0

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self._stage_total[name] += time.perf_counter() - start
            self._stage_calls[name] += 1

    def summary(self) -> str:
        elapsed = time.perf_counter() - self.started
        lines = [f"frames={self.frames} elapsed={elapsed:.1f}s "
                 f"avg_fps={self.frames / elapsed if elapsed > 0 else 0:.1f}"]
        for name, total in sorted(self._stage_total.items()):
            calls = self._stage_calls[name]
            lines.append(f"  {name}: {calls} calls, avg {1000 * total / calls:.1f} ms, total {total:.1f}s")
        return "\n".join(lines)
