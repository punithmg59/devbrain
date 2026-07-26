"""
ReadAheadStrategy abstract interface and SequentialReadAhead implementation.
"""

from abc import ABC, abstractmethod
from typing import List

from graph_storage.cache.prefetch_planner import SimpleSequentialPrefetch


class ReadAheadStrategy(ABC):
    """Abstract strategy interface for planning read-ahead keys."""

    @abstractmethod
    def plan_read_ahead(self, key: str) -> List[str]:
        """Generate list of keys to read ahead."""
        ...


class SequentialReadAhead(ReadAheadStrategy):
    """Sequential read-ahead strategy."""

    def __init__(self, count: int = 2):
        self.count = count
        self._planner = SimpleSequentialPrefetch()

    def plan_read_ahead(self, key: str) -> List[str]:
        results = []
        curr_key = key
        for _ in range(self.count):
            predicted = self._planner.predict_prefetch(curr_key)
            if predicted:
                results.extend(predicted)
                curr_key = predicted[0]
            else:
                break
        return results
