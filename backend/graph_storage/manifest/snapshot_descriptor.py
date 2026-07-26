"""
SnapshotDescriptor model definition.
"""

from dataclasses import dataclass
from typing import Optional

from graph_storage.model import SnapshotId, StorageKey, VersionRef


@dataclass(frozen=True)
class SnapshotDescriptor:
    """Immutable representation of a complete point-in-time graph snapshot."""

    snapshot_id: SnapshotId
    repository_id: str
    version: VersionRef
    created_time: float
    segment_count: int
    total_size: int
    checksum: str
    manifest_location: StorageKey
    parent_snapshot_id: Optional[SnapshotId] = None
