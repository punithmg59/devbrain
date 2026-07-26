"""
Partition event model interfaces.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PartitionCreatedEvent:
    partition_id: str
    partition_name: str
    capacity_bytes: int


@dataclass(frozen=True)
class PartitionDeletedEvent:
    partition_id: str


@dataclass(frozen=True)
class PartitionFullEvent:
    partition_id: str
    current_size_bytes: int
    capacity_bytes: int


@dataclass(frozen=True)
class PartitionBalancedEvent:
    partition_id: str
    utilization_ratio: float


@dataclass(frozen=True)
class PartitionMigratedEvent:
    source_partition_id: str
    target_partition_id: str
    transferred_bytes: int
