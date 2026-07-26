"""
TraceContext model and TracingManager implementation.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TraceContext:
    """Immutable representation of an active or completed trace span."""

    trace_id: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    parent_trace_id: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class TracingManager:
    """Passive, side-effect free tracing manager."""

    def __init__(self):
        self._active_spans: Dict[str, TraceContext] = {}
        self._completed_spans: List[TraceContext] = []

    def start_trace(self, operation: str, parent_id: Optional[str] = None, metadata: Dict[str, str] = None) -> TraceContext:
        """Start a new trace span."""
        tid = f"tr_{uuid.uuid4().hex[:12]}"
        ctx = TraceContext(
            trace_id=tid,
            operation=operation,
            start_time=time.time(),
            parent_trace_id=parent_id,
            metadata=metadata or {},
        )
        self._active_spans[tid] = ctx
        return ctx

    def end_trace(self, trace_id: str) -> Optional[TraceContext]:
        """End an active trace span."""
        if trace_id not in self._active_spans:
            return None

        active = self._active_spans.pop(trace_id)
        now = time.time()
        duration = (now - active.start_time) * 1000.0

        completed = TraceContext(
            trace_id=active.trace_id,
            operation=active.operation,
            start_time=active.start_time,
            end_time=now,
            duration_ms=duration,
            parent_trace_id=active.parent_trace_id,
            metadata=active.metadata,
        )
        self._completed_spans.append(completed)
        return completed

    def get_completed_traces(self) -> List[TraceContext]:
        """Return list of completed trace spans."""
        return list(self._completed_spans)
