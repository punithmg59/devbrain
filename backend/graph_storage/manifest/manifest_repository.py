"""
ManifestRepository implementation for persisting and loading manifest catalog descriptors.
"""

import json
import time
from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError, SegmentNotFoundError
from graph_storage.manifest.manifest_descriptor import ManifestDescriptor
from graph_storage.model import PartitionId, SegmentDescriptor, SegmentId, SegmentMetadata, SnapshotId, StorageKey, VersionRef
from graph_storage.segment.integrity_verifier import IntegrityVerifier
from graph_storage.segment.segment_repository import SegmentRepository


class ManifestRepository:
    """Repository for managing manifest descriptors using SegmentRepository."""

    def __init__(self, segment_repository: SegmentRepository):
        self.segment_repository = segment_repository
        self._manifest_store: Dict[str, ManifestDescriptor] = {}

    def _manifest_segment_id(self, manifest_id: str) -> SegmentId:
        return SegmentId(f"manifest_{manifest_id}")

    def save_manifest(self, manifest: ManifestDescriptor) -> None:
        """Serialize and save manifest descriptor into segment repository."""
        self._manifest_store[manifest.manifest_id] = manifest
        # Encode manifest JSON payload
        entries_json = [
            {
                "seg_id": entry.metadata.segment_id.value,
                "part_id": entry.metadata.partition_id.value,
                "size": entry.metadata.size_bytes,
                "count": entry.metadata.record_count,
                "checksum": entry.metadata.checksum,
                "key": entry.storage_key.value,
            }
            for entry in manifest.segment_entries
        ]
        manifest_dict = {
            "manifest_id": manifest.manifest_id,
            "snapshot_id": manifest.snapshot_id.value,
            "schema_version": f"{manifest.schema_version.major}.{manifest.schema_version.minor}.{manifest.schema_version.patch}",
            "created_time": manifest.created_time,
            "checksum": manifest.checksum,
            "entries": entries_json,
        }
        payload = json.dumps(manifest_dict).encode("utf-8")
        self.segment_repository.save(self._manifest_segment_id(manifest.manifest_id), payload)

    def load_manifest(self, manifest_id: str) -> ManifestDescriptor:
        """Load and deserialize manifest descriptor from segment repository."""
        if manifest_id in self._manifest_store:
            return self._manifest_store[manifest_id]

        seg_id = self._manifest_segment_id(manifest_id)
        if not self.segment_repository.exists(seg_id):
            raise SegmentNotFoundError(f"Manifest not found: {manifest_id}")

        payload = self.segment_repository.load(seg_id)
        manifest_dict = json.loads(payload.decode("utf-8"))

        schema_parts = [int(p) for p in manifest_dict["schema_version"].split(".")]
        schema_ver = VersionRef(schema_parts[0], schema_parts[1], schema_parts[2])

        entries = [
            SegmentDescriptor(
                metadata=SegmentMetadata(
                    segment_id=SegmentId(e["seg_id"]),
                    partition_id=PartitionId(e["part_id"]),
                    size_bytes=e["size"],
                    record_count=e["count"],
                    checksum=e["checksum"],
                ),
                storage_key=StorageKey(e["key"]),
            )
            for e in manifest_dict["entries"]
        ]

        manifest = ManifestDescriptor(
            manifest_id=manifest_dict["manifest_id"],
            snapshot_id=SnapshotId(manifest_dict["snapshot_id"]),
            schema_version=schema_ver,
            segment_entries=entries,
            checksum=manifest_dict["checksum"],
            created_time=manifest_dict["created_time"],
        )
        self._manifest_store[manifest_id] = manifest
        return manifest

    def delete_manifest(self, manifest_id: str) -> bool:
        """Delete manifest from repository."""
        self._manifest_store.pop(manifest_id, None)
        return self.segment_repository.delete(self._manifest_segment_id(manifest_id))

    def exists(self, manifest_id: str) -> bool:
        """Check if manifest exists in repository."""
        if manifest_id in self._manifest_store:
            return True
        return self.segment_repository.exists(self._manifest_segment_id(manifest_id))

    def list(self) -> List[str]:
        """List all manifest IDs."""
        return list(self._manifest_store.keys())
