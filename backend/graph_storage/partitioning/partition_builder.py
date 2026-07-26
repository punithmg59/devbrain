"""
PartitionBuilder for constructing PartitionDescriptor objects.
"""

from typing import Dict, Optional
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor


class PartitionBuilder:
    """Builder pattern for constructing validated PartitionDescriptor instances."""

    def __init__(self):
        self._partition_id: Optional[PartitionId] = None
        self._partition_name: Optional[str] = None
        self._capacity_bytes: int = 1073741824  # 1 GB default
        self._current_size_bytes: int = 0
        self._segment_count: int = 0
        self._status: str = "ACTIVE"
        self._placement_strategy: str = "default"
        self._metadata: Dict[str, str] = {}

    def set_partition_id(self, partition_id: PartitionId) -> "PartitionBuilder":
        self._partition_id = partition_id
        return self

    def set_partition_name(self, name: str) -> "PartitionBuilder":
        self._partition_name = name
        return self

    def set_capacity_bytes(self, capacity: int) -> "PartitionBuilder":
        if capacity <= 0:
            raise GraphStorageError("Partition capacity must be greater than 0")
        self._capacity_bytes = capacity
        return self

    def set_current_size_bytes(self, size: int) -> "PartitionBuilder":
        if size < 0:
            raise GraphStorageError("Partition size cannot be negative")
        self._current_size_bytes = size
        return self

    def set_segment_count(self, count: int) -> "PartitionBuilder":
        if count < 0:
            raise GraphStorageError("Segment count cannot be negative")
        self._segment_count = count
        return self

    def set_status(self, status: str) -> "PartitionBuilder":
        self._status = status
        return self

    def set_placement_strategy(self, strategy: str) -> "PartitionBuilder":
        self._placement_strategy = strategy
        return self

    def set_metadata(self, metadata: Dict[str, str]) -> "PartitionBuilder":
        self._metadata = dict(metadata)
        return self

    def build(self) -> PartitionDescriptor:
        """Construct and validate PartitionDescriptor."""
        if not self._partition_id:
            raise GraphStorageError("PartitionId is required for PartitionBuilder")
        if not self._partition_name:
            self._partition_name = f"part_{self._partition_id.value}"

        if self._current_size_bytes > self._capacity_bytes:
            raise GraphStorageError("Current size cannot exceed total capacity")

        return PartitionDescriptor(
            partition_id=self._partition_id,
            partition_name=self._partition_name,
            capacity_bytes=self._capacity_bytes,
            current_size_bytes=self._current_size_bytes,
            segment_count=self._segment_count,
            status=self._status,
            placement_strategy=self._placement_strategy,
            metadata=self._metadata,
        )
