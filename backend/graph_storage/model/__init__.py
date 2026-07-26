"""
Model package for Graph Storage value objects, descriptors, and domain enums.
"""

from graph_storage.model.enums import ConsistencyModel, LogLevel, ProbePolicy
from graph_storage.model.value_objects import (
    StorageKey,
    SegmentId,
    PartitionId,
    SnapshotId,
    VersionRef,
    LeaseHandle,
    TransactionHandle,
    StorageHealth,
    CacheStatistics,
    ArtifactHeader,
    SegmentMetadata,
    SegmentDescriptor,
    MetricRecord,
    LogRecord,
    StorageEvent,
    TraceContext,
)

__all__ = [
    "ConsistencyModel",
    "LogLevel",
    "ProbePolicy",
    "StorageKey",
    "SegmentId",
    "PartitionId",
    "SnapshotId",
    "VersionRef",
    "LeaseHandle",
    "TransactionHandle",
    "StorageHealth",
    "CacheStatistics",
    "ArtifactHeader",
    "SegmentMetadata",
    "SegmentDescriptor",
    "MetricRecord",
    "LogRecord",
    "StorageEvent",
    "TraceContext",
]
