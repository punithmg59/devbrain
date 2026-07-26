"""
SnapshotBuilder for constructing validated SnapshotDescriptor objects.
"""

import time
from typing import Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.model import SnapshotId, StorageKey, VersionRef


class SnapshotBuilder:
    """Builder pattern for constructing validated SnapshotDescriptor objects."""

    def __init__(self):
        self._snapshot_id: Optional[SnapshotId] = None
        self._repository_id: Optional[str] = None
        self._version: VersionRef = VersionRef(1, 0, 0)
        self._created_time: float = time.time()
        self._segment_count: int = 0
        self._total_size: int = 0
        self._checksum: str = ""
        self._manifest_location: Optional[StorageKey] = None
        self._parent_snapshot_id: Optional[SnapshotId] = None

    def set_snapshot_id(self, snapshot_id: SnapshotId) -> "SnapshotBuilder":
        self._snapshot_id = snapshot_id
        return self

    def set_repository_id(self, repo_id: str) -> "SnapshotBuilder":
        self._repository_id = repo_id
        return self

    def set_version(self, version: VersionRef) -> "SnapshotBuilder":
        self._version = version
        return self

    def set_created_time(self, timestamp: float) -> "SnapshotBuilder":
        self._created_time = timestamp
        return self

    def set_segment_count(self, count: int) -> "SnapshotBuilder":
        if count < 0:
            raise GraphStorageError("Segment count cannot be negative")
        self._segment_count = count
        return self

    def set_total_size(self, size: int) -> "SnapshotBuilder":
        if size < 0:
            raise GraphStorageError("Total size cannot be negative")
        self._total_size = size
        return self

    def set_checksum(self, checksum: str) -> "SnapshotBuilder":
        self._checksum = checksum
        return self

    def set_manifest_location(self, location: StorageKey) -> "SnapshotBuilder":
        self._manifest_location = location
        return self

    def set_parent_snapshot_id(self, parent_id: Optional[SnapshotId]) -> "SnapshotBuilder":
        self._parent_snapshot_id = parent_id
        return self

    def build(self) -> SnapshotDescriptor:
        """Construct and validate SnapshotDescriptor."""
        if not self._snapshot_id:
            raise GraphStorageError("SnapshotId is required for SnapshotBuilder")
        if not self._repository_id:
            raise GraphStorageError("RepositoryId is required for SnapshotBuilder")
        if not self._manifest_location:
            raise GraphStorageError("ManifestLocation is required for SnapshotBuilder")

        return SnapshotDescriptor(
            snapshot_id=self._snapshot_id,
            repository_id=self._repository_id,
            version=self._version,
            created_time=self._created_time,
            segment_count=self._segment_count,
            total_size=self._total_size,
            checksum=self._checksum,
            manifest_location=self._manifest_location,
            parent_snapshot_id=self._parent_snapshot_id,
        )
