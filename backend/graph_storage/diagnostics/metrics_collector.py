"""
MetricRegistry and MetricsCollector implementation.
"""

import threading
from typing import Dict, List, Optional


class MetricRegistry:
    """Registry for counters, gauges, and latency lists."""

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}

    def increment_counter(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe_histogram(self, name: str, value: float) -> None:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = []
            self._histograms[name].append(value)

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        with self._lock:
            return self._gauges.get(name, 0.0)

    def get_histogram(self, name: str) -> List[float]:
        with self._lock:
            return list(self._histograms.get(name, []))

    def snapshot(self) -> Dict[str, Dict]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: list(v) for k, v in self._histograms.items()},
            }


class MetricsCollector:
    """Collector aggregating storage operation metrics."""

    def __init__(self, registry: Optional[MetricRegistry] = None):
        self.registry = registry or MetricRegistry()

    def record_read(self, count: int = 1) -> None:
        self.registry.increment_counter("reads_total", count)

    def record_write(self, count: int = 1) -> None:
        self.registry.increment_counter("writes_total", count)

    def record_cache_hit(self) -> None:
        self.registry.increment_counter("cache_hits_total")

    def record_cache_miss(self) -> None:
        self.registry.increment_counter("cache_misses_total")

    def record_transaction(self) -> None:
        self.registry.increment_counter("transactions_total")

    def record_rollback(self) -> None:
        self.registry.increment_counter("rollbacks_total")

    def set_memory_usage(self, bytes_val: int) -> None:
        self.registry.set_gauge("memory_usage_bytes", float(bytes_val))

    def set_storage_usage(self, bytes_val: int) -> None:
        self.registry.set_gauge("storage_usage_bytes", float(bytes_val))
