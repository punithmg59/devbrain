"""
LatencyHistogram model and PerformanceProfiler implementation.
"""

import math
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class LatencyHistogram:
    """Immutable latency percentile histogram."""

    p50: float
    p90: float
    p95: float
    p99: float
    min_ms: float
    max_ms: float
    avg_ms: float


class PerformanceProfiler:
    """Profiler collecting and calculating operation performance metrics."""

    def __init__(self):
        self._latencies: Dict[str, List[float]] = {}

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record operation latency in milliseconds."""
        if operation not in self._latencies:
            self._latencies[operation] = []
        self._latencies[operation].append(latency_ms)

    def calculate_histogram(self, operation: str) -> LatencyHistogram:
        """Calculate percentile histogram for an operation."""
        samples = sorted(self._latencies.get(operation, []))
        if not samples:
            return LatencyHistogram(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        n = len(samples)
        p50 = samples[int(n * 0.50)]
        p90 = samples[min(int(n * 0.90), n - 1)]
        p95 = samples[min(int(n * 0.95), n - 1)]
        p99 = samples[min(int(n * 0.99), n - 1)]

        return LatencyHistogram(
            p50=p50,
            p90=p90,
            p95=p95,
            p99=p99,
            min_ms=samples[0],
            max_ms=samples[-1],
            avg_ms=sum(samples) / n,
        )
