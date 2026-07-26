"""
CacheRepository abstract interface and InMemoryCacheRepository implementation.
"""

import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from graph_storage.cache.cache_entry import CacheEntry


class CacheRepository(ABC):
    """Abstract interface for cache storage repository."""

    @abstractmethod
    def store(self, entry: CacheEntry) -> None: ...

    @abstractmethod
    def load(self, key: str) -> Optional[CacheEntry]: ...

    @abstractmethod
    def remove(self, key: str) -> bool: ...

    @abstractmethod
    def contains(self, key: str) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def list_keys(self) -> List[str]: ...

    @abstractmethod
    def list_entries(self) -> List[CacheEntry]: ...


class InMemoryCacheRepository(CacheRepository):
    """Thread-safe in-memory cache repository."""

    def __init__(self):
        self._entries: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def store(self, entry: CacheEntry) -> None:
        with self._lock:
            self._entries[entry.cache_key] = entry

    def load(self, key: str) -> Optional[CacheEntry]:
        with self._lock:
            return self._entries.get(key)

    def remove(self, key: str) -> bool:
        with self._lock:
            return self._entries.pop(key, None) is not None

    def contains(self, key: str) -> bool:
        with self._lock:
            return key in self._entries

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def list_keys(self) -> List[str]:
        with self._lock:
            return list(self._entries.keys())

    def list_entries(self) -> List[CacheEntry]:
        with self._lock:
            return list(self._entries.values())
