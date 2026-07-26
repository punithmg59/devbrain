"""
ManifestManager implementation orchestrating manifest catalog operations.
"""

import time
import uuid
from typing import List

from graph_storage.exceptions import GraphStorageError
from graph_storage.manifest.manifest_descriptor import ManifestDescriptor
from graph_storage.manifest.manifest_repository import ManifestRepository
from graph_storage.manifest.snapshot_validator import SnapshotValidator
from graph_storage.model import SegmentDescriptor, SnapshotId, VersionRef
from graph_storage.segment.integrity_verifier import IntegrityVerifier
from graph_storage.segment.segment_repository import SegmentRepository


class ManifestManager:
    """Manager for building, persisting, loading, and validating manifest catalogs."""

    def __init__(self, manifest_repository: ManifestRepository, segment_repository: SegmentRepository):
        self.manifest_repository = manifest_repository
        self.segment_repository = segment_repository

    def create_manifest(
        self,
        snapshot_id: SnapshotId,
        segment_entries: List[SegmentDescriptor],
        schema_version: VersionRef = VersionRef(1, 0, 0),
    ) -> ManifestDescriptor:
        """Create and persist a new manifest descriptor for segment entries."""
        if not segment_entries:
            raise GraphStorageError("Cannot create manifest with zero segment entries")

        manifest_id = f"m_{uuid.uuid4().hex[:12]}"
        checksum_payload = "".join(e.metadata.checksum for e in segment_entries).encode("utf-8")
        manifest_checksum = IntegrityVerifier.generate_checksum(checksum_payload)

        manifest = ManifestDescriptor(
            manifest_id=manifest_id,
            snapshot_id=snapshot_id,
            schema_version=schema_version,
            segment_entries=segment_entries,
            checksum=manifest_checksum,
            created_time=time.time(),
        )

        SnapshotValidator.validate_manifest(manifest)
        SnapshotValidator.validate_segment_references(manifest, self.segment_repository)
        self.manifest_repository.save_manifest(manifest)
        return manifest

    def load_manifest(self, manifest_id: str) -> ManifestDescriptor:
        """Load manifest descriptor by ID."""
        manifest = self.manifest_repository.load_manifest(manifest_id)
        SnapshotValidator.validate_manifest(manifest)
        return manifest

    def update_manifest(self, manifest: ManifestDescriptor) -> None:
        """Update and persist an existing manifest descriptor."""
        SnapshotValidator.validate_manifest(manifest)
        SnapshotValidator.validate_segment_references(manifest, self.segment_repository)
        self.manifest_repository.save_manifest(manifest)

    def validate_manifest(self, manifest_id: str) -> bool:
        """Validate manifest existence and segment references."""
        try:
            manifest = self.load_manifest(manifest_id)
            SnapshotValidator.validate_segment_references(manifest, self.segment_repository)
            return True
        except Exception:
            return False
