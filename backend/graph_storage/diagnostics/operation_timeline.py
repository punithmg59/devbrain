"""
OperationTimeline implementation for chronological debugging.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TimelineRecord:
    """Immutable record of an operation event in the timeline."""

    record_id: str
    operation: str
    timestamp: float
    duration_ms: float
    status: str
    metadata: Dict[str, str] = field(default_factory=dict)


class OperationTimeline:
    """Chronological event recorder for debugging operational sequences."""

    def __init__(self):
        self._records: List[TimelineRecord] = []
        self._lock = threading.RLock()

    def record_operation(
        self, operation: str, duration_ms: float, status: str = "SUCCESS", metadata: Dict[str, str] = None
    ) -> TimelineRecord:
        """Record an operation in the timeline."""
        rec = TimelineRecord(
            record_id=f"rec_{len(self._records) + 1}",
            operation=operation,
            timestamp=time.time(),
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {},
        )
        with self._lock:
            self._records.append(rec)
        return rec

    def get_timeline(self, limit: int = 100) -> List[TimelineRecord]:
        """Retrieve recent timeline records."""
        with self._lock:
            return list(self._records[-limit:])
