"""
PartitionValidator for verifying partition descriptors, capacities, and placement consistency.
"""

from typing import List, Set
from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor


class PartitionValidator:
    """Validator enforcing partition integrity, limits, and placement rules."""

    @classmethod
    def validate_descriptor(cls, descriptor: PartitionDescriptor) -> None:
        """Validate partition descriptor values."""
        if not descriptor.partition_id or not descriptor.partition_id.value:
            raise GraphStorageError("Partition ID cannot be empty")
        if not descriptor.partition_name:
            raise GraphStorageError("Partition name cannot be empty")
        if descriptor.capacity_bytes <= 0:
            raise GraphStorageError("Partition capacity must be positive")
        if descriptor.current_size_bytes < 0:
            raise GraphStorageError("Partition size cannot be negative")

    @classmethod
    def validate_capacity(cls, descriptor: PartitionDescriptor, additional_bytes: int = 0) -> None:
        """Verify that current size + additional_bytes does not exceed capacity."""
        if descriptor.current_size_bytes + additional_bytes > descriptor.capacity_bytes:
            raise GraphStorageError(
                f"Partition '{descriptor.partition_id.value}' capacity exceeded: "
                f"{descriptor.current_size_bytes + additional_bytes} > {descriptor.capacity_bytes}"
            )

    @classmethod
    def validate_placement_consistency(cls, partitions: List[PartitionDescriptor]) -> None:
        """Verify unique partition IDs across active partitions."""
        seen_ids: Set[PartitionId] = set()
        for p in partitions:
            if p.partition_id in seen_ids:
                raise GraphStorageError(f"Duplicate partition ID detected: '{p.partition_id.value}'")
            seen_ids.add(p.partition_id)

    @classmethod
    def validate_duplicate_segments(cls, segment_ids: List[SegmentId]) -> None:
        """Check for duplicate segment references."""
        seen = set()
        for sid in segment_ids:
            if sid in seen:
                raise GraphStorageError(f"Duplicate segment ID in partition assignment: '{sid.value}'")
            seen.add(sid)
