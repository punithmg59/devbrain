"""
MemoryBackend implementation for Graph Storage.
"""

import hashlib
import threading
from typing import Dict, List

from graph_storage.backend.storage_backend import StorageBackend
from graph_storage.exceptions import SegmentNotFoundError
from graph_storage.model import (
    PartitionId,
    SegmentDescriptor,
    SegmentId,
    SegmentMetadata,
    StorageHealth,
    StorageKey,
)


class MemoryBackend(StorageBackend):
    """Thread-safe in-memory storage backend using SegmentId object keys."""

    def __init__(self):
        self._store: Dict[SegmentId, bytes] = {}
        self._lock = threading.RLock()

    def exists_segment(self, segment_id: SegmentId) -> bool:
        with self._lock:
            return segment_id in self._store

    def read_segment(self, segment_id: SegmentId) -> bytes:
        with self._lock:
            if segment_id not in self._store:
                raise SegmentNotFoundError(f"Segment not found in memory: {segment_id.value}")
            return self._store[segment_id]

    def write_segment(self, segment_id: SegmentId, data: bytes) -> SegmentDescriptor:
        with self._lock:
            self._store[segment_id] = data
            checksum = hashlib.sha256(data).hexdigest()
            metadata = SegmentMetadata(
                segment_id=segment_id,
                partition_id=PartitionId("memory_default"),
                size_bytes=len(data),
                record_count=1,
                checksum=checksum,
            )
            return SegmentDescriptor(
                metadata=metadata,
                storage_key=StorageKey(f"mem://{segment_id.value}"),
            )

    def delete_segment(self, segment_id: SegmentId) -> bool:
        with self._lock:
            if segment_id in self._store:
                del self._store[segment_id]
                return True
            return False

    def list_segments(self) -> List[SegmentDescriptor]:
        with self._lock:
            descriptors: List[SegmentDescriptor] = []
            for segment_id, data in self._store.items():
                checksum = hashlib.sha256(data).hexdigest()
                metadata = SegmentMetadata(
                    segment_id=segment_id,
                    partition_id=PartitionId("memory_default"),
                    size_bytes=len(data),
                    record_count=1,
                    checksum=checksum,
                )
                descriptors.append(
                    SegmentDescriptor(
                        metadata=metadata,
                        storage_key=StorageKey(f"mem://{segment_id.value}"),
                    )
                )
            return descriptors

    def health(self) -> StorageHealth:
        with self._lock:
            used = sum(len(b) for b in self._store.values())
            return StorageHealth(
                is_healthy=True,
                status_message="Memory backend operational",
                available_bytes=1073741824,
                used_bytes=used,
            )
