"""
ManifestBuilder for constructing ManifestDescriptor objects with deduplication and sorting.
"""

import time
from typing import List, Optional

from graph_storage.exceptions import GraphStorageError
from graph_storage.manifest.manifest_descriptor import ManifestDescriptor
from graph_storage.model import SegmentDescriptor, SnapshotId, VersionRef
from graph_storage.segment.integrity_verifier import IntegrityVerifier


class ManifestBuilder:
    """Builder pattern for constructing ManifestDescriptor objects with deduplication and sorting."""

    def __init__(self):
        self._manifest_id: Optional[str] = None
        self._snapshot_id: Optional[SnapshotId] = None
        self._schema_version: VersionRef = VersionRef(1, 0, 0)
        self._entries: List[SegmentDescriptor] = []
        self._created_time: float = time.time()

    def set_manifest_id(self, manifest_id: str) -> "ManifestBuilder":
        self._manifest_id = manifest_id
        return self

    def set_snapshot_id(self, snapshot_id: SnapshotId) -> "ManifestBuilder":
        self._snapshot_id = snapshot_id
        return self

    def set_schema_version(self, version: VersionRef) -> "ManifestBuilder":
        self._schema_version = version
        return self

    def set_created_time(self, timestamp: float) -> "ManifestBuilder":
        self._created_time = timestamp
        return self

    def add_segment_entry(self, entry: SegmentDescriptor) -> "ManifestBuilder":
        self._entries.append(entry)
        return self

    def add_segment_entries(self, entries: List[SegmentDescriptor]) -> "ManifestBuilder":
        self._entries.extend(entries)
        return self

    def build(self) -> ManifestDescriptor:
        """Construct and validate ManifestDescriptor with deduplication and sorting."""
        if not self._manifest_id:
            raise GraphStorageError("ManifestId is required for ManifestBuilder")
        if not self._snapshot_id:
            raise GraphStorageError("SnapshotId is required for ManifestBuilder")
        if not self._entries:
            raise GraphStorageError("Segment entries cannot be empty in ManifestBuilder")

        # Deduplicate entries by segment_id
        unique_entries: List[SegmentDescriptor] = []
        seen_ids = set()
        for entry in self._entries:
            seg_id = entry.metadata.segment_id
            if seg_id not in seen_ids:
                seen_ids.add(seg_id)
                unique_entries.append(entry)

        # Deterministic sorting by segment ID value
        sorted_entries = sorted(unique_entries, key=lambda e: e.metadata.segment_id.value)

        # Compute payload checksum
        checksum_payload = "".join(e.metadata.checksum for e in sorted_entries).encode("utf-8")
        computed_checksum = IntegrityVerifier.generate_checksum(checksum_payload)

        return ManifestDescriptor(
            manifest_id=self._manifest_id,
            snapshot_id=self._snapshot_id,
            schema_version=self._schema_version,
            segment_entries=sorted_entries,
            checksum=computed_checksum,
            created_time=self._created_time,
        )
