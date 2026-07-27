# backend/graph_query_engine/optimizer/diagnostics.py
"""Diagnostics collection for the Planner Optimizer.
Thread‑safe collection of rule application statistics and timestamps.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict

@dataclass(frozen=True)
class AppliedRuleInfo:
    name: str
    timestamp: datetime
    details: str = ""

@dataclass(frozen=True)
class SkippedRuleInfo:
    name: str
    timestamp: datetime
    reason: str = ""

@dataclass(frozen=True)
class RejectedRuleInfo:
    name: str
    timestamp: datetime
    error: str = ""

class OptimizationDiagnostics:
    """Thread‑safe diagnostics collector.

    Instances are mutable, but the collected records are immutable dataclasses.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._applied: List[AppliedRuleInfo] = []
        self._skipped: List[SkippedRuleInfo] = []
        self._rejected: List[RejectedRuleInfo] = []

    # ---------- mutation helpers ----------
    def record_applied(self, name: str, details: str = "") -> None:
        with self._lock:
            self._applied.append(AppliedRuleInfo(name=name, timestamp=datetime.utcnow(), details=details))

    def record_skipped(self, name: str, reason: str = "") -> None:
        with self._lock:
            self._skipped.append(SkippedRuleInfo(name=name, timestamp=datetime.utcnow(), reason=reason))

    def record_rejected(self, name: str, error: str = "") -> None:
        with self._lock:
            self._rejected.append(RejectedRuleInfo(name=name, timestamp=datetime.utcnow(), error=error))

    # ---------- read‑only accessors ----------
    @property
    def applied(self) -> List[AppliedRuleInfo]:
        with self._lock:
            return list(self._applied)

    @property
    def skipped(self) -> List[SkippedRuleInfo]:
        with self._lock:
            return list(self._skipped)

    @property
    def rejected(self) -> List[RejectedRuleInfo]:
        with self._lock:
            return list(self._rejected)

    def summary(self) -> Dict[str, int]:
        """Return a quick count summary for reporting purposes."""
        with self._lock:
            return {
                "applied": len(self._applied),
                "skipped": len(self._skipped),
                "rejected": len(self._rejected),
            }

__all__ = ["OptimizationDiagnostics", "AppliedRuleInfo", "SkippedRuleInfo", "RejectedRuleInfo"]
