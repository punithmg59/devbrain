"""
PartitionDescriptor model definition.
"""

from dataclasses import dataclass, field
from typing import Dict
from graph_storage.model import PartitionId


@dataclass(frozen=True)
class PartitionDescriptor:
    """Immutable metadata descriptor for a storage partition."""

    partition_id: PartitionId
    partition_name: str
    capacity_bytes: int
    current_size_bytes: int
    segment_count: int
    status: str
    placement_strategy: str
    metadata: Dict[str, str] = field(default_factory=dict)
