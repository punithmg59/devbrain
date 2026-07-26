"""
ManifestDescriptor model definition.
"""

from dataclasses import dataclass
from typing import List

from graph_storage.model import SegmentDescriptor, SnapshotId, VersionRef


@dataclass(frozen=True)
class ManifestDescriptor:
    """Immutable manifest catalog for a snapshot's storage segments."""

    manifest_id: str
    snapshot_id: SnapshotId
    schema_version: VersionRef
    segment_entries: List[SegmentDescriptor]
    checksum: str
    created_time: float
