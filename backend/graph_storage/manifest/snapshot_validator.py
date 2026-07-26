"""
SnapshotValidator for verifying snapshot integrity, segment references, and manifests.
"""

from graph_storage.exceptions import ChecksumMismatchError, GraphStorageError, SegmentNotFoundError
from graph_storage.manifest.manifest_descriptor import ManifestDescriptor
from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.segment.integrity_verifier import IntegrityVerifier
from graph_storage.segment.segment_repository import SegmentRepository


class SnapshotValidator:
    """Validator enforcing snapshot, manifest, and segment reference constraints."""

    @classmethod
    def validate_snapshot(cls, snapshot: SnapshotDescriptor) -> None:
        """Validate snapshot descriptor fields."""
        if not snapshot.snapshot_id or not snapshot.snapshot_id.value:
            raise GraphStorageError("Snapshot ID cannot be empty")
        if not snapshot.repository_id:
            raise GraphStorageError("Repository ID cannot be empty")
        if snapshot.segment_count < 0:
            raise GraphStorageError("Segment count cannot be negative")

    @classmethod
    def validate_manifest(cls, manifest: ManifestDescriptor) -> None:
        """Validate manifest entries and structure."""
        if not manifest.manifest_id:
            raise GraphStorageError("Manifest ID cannot be empty")
        if not manifest.segment_entries:
            raise GraphStorageError("Manifest segment entries cannot be empty")

    @classmethod
    def validate_segment_references(cls, manifest: ManifestDescriptor, segment_repository: SegmentRepository) -> None:
        """Verify that all segments referenced by a manifest exist in segment repository."""
        for entry in manifest.segment_entries:
            seg_id = entry.metadata.segment_id
            if not segment_repository.exists(seg_id):
                raise SegmentNotFoundError(f"Missing referenced segment: {seg_id.value}")

    @classmethod
    def validate_checksum(cls, data: bytes, expected_checksum: str) -> None:
        """Verify checksum integrity."""
        if not IntegrityVerifier.verify_checksum(data, expected_checksum):
            raise ChecksumMismatchError("Snapshot or manifest checksum mismatch")

    @classmethod
    def validate_schema(cls, current_schema_major: int, expected_schema_major: int) -> None:
        """Verify schema version compatibility."""
        if current_schema_major > expected_schema_major:
            raise GraphStorageError(
                f"Unsupported schema version: {current_schema_major}, expected <= {expected_schema_major}"
            )
