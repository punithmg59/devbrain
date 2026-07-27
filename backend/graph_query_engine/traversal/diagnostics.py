# backend/graph_query_engine/traversal/diagnostics.py
"""Thread-safe diagnostics collection during graph traversal execution.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TraversalDiagnosticRecord(BaseModel):
    """Immutable single diagnostic entry."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field("INFO", description="Diagnostic severity level (INFO, WARNING, ERROR)")
    category: str = Field("Execution", description="Category (Algorithm, Operator, Pruning, Cache)")
    message: str = Field(..., description="Human-readable diagnostic description")
    details: Dict[str, Any] = Field(default_factory=dict)


class TraversalDiagnostics:
    """Thread-safe diagnostic accumulator for graph traversal runs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: List[TraversalDiagnosticRecord] = []
        self._algorithm_used: str = "Unknown"
        self._pruning_stats: Dict[str, int] = {}
        self._cache_stats: Dict[str, int] = {"hits": 0, "misses": 0}

    def record_info(self, category: str, message: str, **details) -> None:
        with self._lock:
            self._records.append(
                TraversalDiagnosticRecord(level="INFO", category=category, message=message, details=details)
            )

    def record_warning(self, category: str, message: str, **details) -> None:
        with self._lock:
            self._records.append(
                TraversalDiagnosticRecord(level="WARNING", category=category, message=message, details=details)
            )

    def record_error(self, category: str, message: str, **details) -> None:
        with self._lock:
            self._records.append(
                TraversalDiagnosticRecord(level="ERROR", category=category, message=message, details=details)
            )

    def set_algorithm(self, name: str) -> None:
        with self._lock:
            self._algorithm_used = name

    def record_pruning(self, reason: str, count: int = 1) -> None:
        with self._lock:
            self._pruning_stats[reason] = self._pruning_stats.get(reason, 0) + count

    def record_cache_hit(self) -> None:
        with self._lock:
            self._cache_stats["hits"] += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self._cache_stats["misses"] += 1

    @property
    def records(self) -> List[TraversalDiagnosticRecord]:
        with self._lock:
            return list(self._records)

    @property
    def warnings(self) -> List[str]:
        with self._lock:
            return [r.message for r in self._records if r.level == "WARNING"]

    @property
    def errors(self) -> List[str]:
        with self._lock:
            return [r.message for r in self._records if r.level == "ERROR"]

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "algorithm_used": self._algorithm_used,
                "total_diagnostics": len(self._records),
                "warnings_count": len([r for r in self._records if r.level == "WARNING"]),
                "errors_count": len([r for r in self._records if r.level == "ERROR"]),
                "pruning_stats": dict(self._pruning_stats),
                "cache_stats": dict(self._cache_stats),
            }


__all__ = ["TraversalDiagnosticRecord", "TraversalDiagnostics"]
