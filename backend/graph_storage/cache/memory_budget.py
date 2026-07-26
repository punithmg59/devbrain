"""
MemoryBudget component for tracking memory allocations and capacity limits.
"""

import threading
from graph_storage.exceptions import GraphStorageError


class MemoryBudget:
    """Thread-safe memory budget tracker."""

    def __init__(self, limit_bytes: int = 104857600):
        if limit_bytes <= 0:
            raise GraphStorageError("Memory budget limit must be positive")
        self._limit_bytes = limit_bytes
        self._used_bytes = 0
        self._lock = threading.RLock()

    @property
    def limit(self) -> int:
        with self._lock:
            return self._limit_bytes

    @property
    def used(self) -> int:
        with self._lock:
            return self._used_bytes

    @property
    def headroom(self) -> int:
        with self._lock:
            return max(0, self._limit_bytes - self._used_bytes)

    def can_allocate(self, size_bytes: int) -> bool:
        with self._lock:
            return (self._used_bytes + size_bytes) <= self._limit_bytes

    def allocate(self, size_bytes: int) -> bool:
        with self._lock:
            if not self.can_allocate(size_bytes):
                return False
            self._used_bytes += size_bytes
            return True

    def release(self, size_bytes: int) -> None:
        with self._lock:
            self._used_bytes = max(0, self._used_bytes - size_bytes)
