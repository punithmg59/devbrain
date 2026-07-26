"""
SnapshotManager implementation orchestrating snapshot lifecycle and manifest associations.
"""

import time
import uuid
from typing import List, Optional

from graph_storage.exceptions import GraphStorageError, SegmentNotFoundError
from graph_storage.manifest.manifest_manager import ManifestManager
from graph_storage.manifest.manifest_repository import ManifestRepository
from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.manifest.snapshot_history import SnapshotHistory
from graph_storage.manifest.snapshot_repository import SnapshotRepository
from graph_storage.manifest.snapshot_validator import SnapshotValidator
from graph_storage.model import SegmentDescriptor, SnapshotId, StorageKey, VersionRef
from graph_storage.segment.integrity_verifier import IntegrityVerifier
from graph_storage.segment.segment_repository import SegmentRepository


class SnapshotManager:
    """High-level manager for creating, loading, deleting, and querying repository graph snapshots."""

    def __init__(
        self,
        snapshot_repository: SnapshotRepository,
        manifest_repository: ManifestRepository,
        segment_repository: SegmentRepository,
    ):
        self.snapshot_repository = snapshot_repository
        self.manifest_repository = manifest_repository
        self.segment_repository = segment_repository

        self.manifest_manager = ManifestManager(manifest_repository, segment_repository)
        self.history_tracker = SnapshotHistory(snapshot_repository)

    def create_snapshot(
        self,
        repository_id: str,
        segment_entries: List[SegmentDescriptor],
        version: VersionRef = VersionRef(1, 0, 0),
        parent_snapshot_id: Optional[SnapshotId] = None,
    ) -> SnapshotDescriptor:
        """Create a complete point-in-time repository snapshot and associated manifest catalog."""
        if not segment_entries:
            raise GraphStorageError("Cannot create a snapshot with zero segment entries")

        snapshot_id = SnapshotId(f"snap_{uuid.uuid4().hex[:12]}")
        manifest = self.manifest_manager.create_manifest(snapshot_id, segment_entries, schema_version=version)

        total_size = sum(e.metadata.size_bytes for e in segment_entries)
        checksum_input = f"{snapshot_id.value}:{manifest.checksum}:{total_size}".encode("utf-8")
        snapshot_checksum = IntegrityVerifier.generate_checksum(checksum_input)

        descriptor = SnapshotDescriptor(
            snapshot_id=snapshot_id,
            repository_id=repository_id,
            version=version,
            created_time=time.time(),
            segment_count=len(segment_entries),
            total_size=total_size,
            checksum=snapshot_checksum,
            manifest_location=StorageKey(manifest.manifest_id),
            parent_snapshot_id=parent_snapshot_id,
        )

        SnapshotValidator.validate_snapshot(descriptor)
        self.snapshot_repository.save_snapshot(descriptor)
        return descriptor

    def load_snapshot(self, snapshot_id: SnapshotId) -> SnapshotDescriptor:
        """Load snapshot descriptor by ID."""
        descriptor = self.snapshot_repository.load_snapshot(snapshot_id)
        SnapshotValidator.validate_snapshot(descriptor)
        return descriptor

    def delete_snapshot(self, snapshot_id: SnapshotId, delete_manifest: bool = True) -> bool:
        """Delete a snapshot descriptor and optionally its associated manifest catalog."""
        descriptor = self.load_snapshot(snapshot_id)
        if delete_manifest and descriptor.manifest_location:
            self.manifest_repository.delete_manifest(descriptor.manifest_location.value)
        return self.snapshot_repository.delete_snapshot(snapshot_id)

    def latest_snapshot(self, repository_id: str) -> Optional[SnapshotDescriptor]:
        """Retrieve latest snapshot descriptor for a repository."""
        return self.snapshot_repository.latest(repository_id)

    def list_snapshots(self, repository_id: str) -> List[SnapshotDescriptor]:
        """List all snapshots for a repository in creation order."""
        return self.snapshot_repository.history(repository_id)

    def snapshot_exists(self, snapshot_id: SnapshotId) -> bool:
        """Check if snapshot descriptor exists."""
        return self.snapshot_repository.exists(snapshot_id)
