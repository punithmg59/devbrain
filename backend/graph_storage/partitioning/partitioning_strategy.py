"""
PartitioningStrategy abstract interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class PartitioningStrategy(ABC):
    """Abstract interface for artifact storage partitioning policies."""

    @abstractmethod
    def choose_partition(self, artifact_id: str, metadata: Dict[str, Any]) -> str:
        """Select a partition location for an artifact given its ID and metadata."""
        ...

    @abstractmethod
    def partition_key(self, artifact_id: str) -> str:
        """Generate the partition key for a given artifact ID."""
        ...

    @abstractmethod
    def validate_partition(self, partition_key: str) -> bool:
        """Validate whether a partition key satisfies strategy requirements."""
        ...
