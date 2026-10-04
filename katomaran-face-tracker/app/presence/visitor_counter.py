"""Unique visitor counting.

Semantics (documented in docs/ASSUMPTIONS.md)
---------------------------------------------
unique_visitor_count = number of DISTINCT Face IDs, never the number of detections,
tracks or ENTRY events.

scope = "all_time" (default): every person registered in the database, including
        previous runs. Survives restarts. Equals ``SELECT COUNT(*) FROM faces``.
scope = "session": distinct Face IDs seen since THIS run started.
"""

from __future__ import annotations

from typing import Callable, Set


class VisitorCounter:
    def __init__(self, scope: str, registered_count: Callable[[], int]) -> None:
        self._scope = scope
        self._registered_count = registered_count
        self._session_ids: Set[str] = set()

    def observe(self, face_id: str) -> None:
        self._session_ids.add(face_id)

    @property
    def count(self) -> int:
        return len(self._session_ids) if self._scope == "session" else self._registered_count()
