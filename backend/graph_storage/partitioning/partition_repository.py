"""
PartitionRepository abstract interface and DefaultPartitionRepository implementation.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.model import PartitionId, SegmentId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor
from graph_storage.segment.segment_repository import SegmentRepository


class PartitionRepository(ABC):
    """Abstract interface for partition metadata persistence."""

    @abstractmethod
    def save_partition(self, descriptor: PartitionDescriptor) -> None: ...

    @abstractmethod
    def load_partition(self, partition_id: PartitionId) -> PartitionDescriptor: ...

    @abstractmethod
    def delete_partition(self, partition_id: PartitionId) -> bool: ...

    @abstractmethod
    def exists(self, partition_id: PartitionId) -> bool: ...

    @abstractmethod
    def list(self) -> List[PartitionDescriptor]: ...

    @abstractmethod
    def lookup(self, partition_name: str) -> Optional[PartitionDescriptor]: ...


class DefaultPartitionRepository(PartitionRepository):
    """Default partition repository persisting descriptors into memory and segment storage."""

    def __init__(self, segment_repository: Optional[SegmentRepository] = None):
        self.segment_repository = segment_repository
        self._store: Dict[PartitionId, PartitionDescriptor] = {}

    def save_partition(self, descriptor: PartitionDescriptor) -> None:
        self._store[descriptor.partition_id] = descriptor
        if self.segment_repository:
            seg_id = SegmentId(f"partition_{descriptor.partition_id.value}")
            data_dict = {
                "partition_id": descriptor.partition_id.value,
                "partition_name": descriptor.partition_name,
                "capacity_bytes": descriptor.capacity_bytes,
                "current_size_bytes": descriptor.current_size_bytes,
                "segment_count": descriptor.segment_count,
                "status": descriptor.status,
                "placement_strategy": descriptor.placement_strategy,
                "metadata": descriptor.metadata,
            }
            self.segment_repository.save(seg_id, json.dumps(data_dict).encode("utf-8"))

    def load_partition(self, partition_id: PartitionId) -> PartitionDescriptor:
        if partition_id in self._store:
            return self._store[partition_id]

        if self.segment_repository:
            seg_id = SegmentId(f"partition_{partition_id.value}")
            if self.segment_repository.exists(seg_id):
                payload = self.segment_repository.load(seg_id)
                d = json.loads(payload.decode("utf-8"))
                desc = PartitionDescriptor(
                    partition_id=PartitionId(d["partition_id"]),
                    partition_name=d["partition_name"],
                    capacity_bytes=d["capacity_bytes"],
                    current_size_bytes=d["current_size_bytes"],
                    segment_count=d["segment_count"],
                    status=d["status"],
                    placement_strategy=d["placement_strategy"],
                    metadata=d.get("metadata", {}),
                )
                self._store[partition_id] = desc
                return desc

        raise GraphStorageError(f"Partition not found: '{partition_id.value}'")

    def delete_partition(self, partition_id: PartitionId) -> bool:
        existed = partition_id in self._store
        self._store.pop(partition_id, None)
        if self.segment_repository:
            seg_id = SegmentId(f"partition_{partition_id.value}")
            if self.segment_repository.exists(seg_id):
                self.segment_repository.delete(seg_id)
                existed = True
        return existed

    def exists(self, partition_id: PartitionId) -> bool:
        if partition_id in self._store:
            return True
        if self.segment_repository:
            return self.segment_repository.exists(SegmentId(f"partition_{partition_id.value}"))
        return False

    def list(self) -> List[PartitionDescriptor]:
        return list(self._store.values())

    def lookup(self, partition_name: str) -> Optional[PartitionDescriptor]:
        for desc in self.list():
            if desc.partition_name == partition_name:
                return desc
        return None
