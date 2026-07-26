"""
Immutable domain value objects and descriptors for Graph Storage.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from graph_storage.model.enums import LogLevel


@dataclass(frozen=True)
class StorageKey:
    """Immutable unique key identifying a storage location or artifact."""
    value: str


@dataclass(frozen=True)
class SegmentId:
    """Immutable identifier for a physical or logical storage segment."""
    value: str


@dataclass(frozen=True)
class PartitionId:
    """Immutable identifier for a storage partition."""
    value: str


@dataclass(frozen=True)
class SnapshotId:
    """Immutable identifier for a storage point-in-time snapshot."""
    value: str


@dataclass(frozen=True)
class TransactionId:
    """Immutable identifier for a storage transaction."""
    value: str


@dataclass(frozen=True)
class VersionRef:
    """Immutable reference to a storage schema or snapshot version."""
    major: int
    minor: int
    patch: int


@dataclass(frozen=True)
class LeaseHandle:
    """Immutable lease token for resource lock management."""
    lease_id: str
    resource_key: StorageKey
    expires_at_epoch_sec: float


@dataclass(frozen=True)
class TransactionHandle:
    """Immutable handle identifying an active storage transaction."""
    transaction_id: str
    is_write: bool
    snapshot_id: SnapshotId


@dataclass(frozen=True)
class StorageHealth:
    """Immutable storage health status metrics."""
    is_healthy: bool
    status_message: str
    available_bytes: int
    used_bytes: int


@dataclass(frozen=True)
class CacheStatistics:
    """Immutable segment cache performance statistics."""
    hit_count: int
    miss_count: int
    eviction_count: int
    total_bytes_cached: int


@dataclass(frozen=True)
class ArtifactHeader:
    """Descriptor header embedded at the start of binary storage artifacts."""
    magic_bytes: bytes
    schema_version: VersionRef
    payload_size_bytes: int
    checksum: str


@dataclass(frozen=True)
class SegmentMetadata:
    """Metadata describing a single storage segment."""
    segment_id: SegmentId
    partition_id: PartitionId
    size_bytes: int
    record_count: int
    checksum: str


@dataclass(frozen=True)
class SegmentDescriptor:
    """Complete descriptor referencing a physical segment and its storage location."""
    metadata: SegmentMetadata
    storage_key: StorageKey
