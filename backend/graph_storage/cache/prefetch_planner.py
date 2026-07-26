"""
PrefetchPlanner abstract interface and SimpleSequentialPrefetch implementation.
"""

import re
from abc import ABC, abstractmethod
from typing import List


class PrefetchPlanner(ABC):
    """Abstract interface for prefetch prediction."""

    @abstractmethod
    def predict_prefetch(self, key: str) -> List[str]:
        """Predict keys to prefetch based on access key."""
        ...


class SimpleSequentialPrefetch(PrefetchPlanner):
    """Simple sequential key prefetch planner (e.g. seg_1 -> seg_2)."""

    def predict_prefetch(self, key: str) -> List[str]:
        match = re.search(r"(\d+)$", key)
        if match:
            num_str = match.group(1)
            num = int(num_str)
            next_num_str = str(num + 1).zfill(len(num_str))
            prefix = key[: match.start(1)]
            return [f"{prefix}{next_num_str}"]
        return []
