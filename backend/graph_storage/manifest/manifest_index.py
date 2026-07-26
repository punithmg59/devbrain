"""
ManifestIndex query service for indexing manifests, snapshots, and segment reverse lookups.
"""

from typing import Dict, List, Optional, Set

from graph_storage.manifest.manifest_descriptor import ManifestDescriptor
from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.model import SegmentDescriptor, SegmentId, SnapshotId


class ManifestIndex:
    """In-memory indexing query service for manifests, snapshots, and segment usage."""

    def __init__(self):
        self._manifests: Dict[str, ManifestDescriptor] = {}
        self._snapshots: Dict[SnapshotId, SnapshotDescriptor] = {}
        self._segment_to_snapshots: Dict[SegmentId, Set[SnapshotId]] = {}
        self._segment_to_manifests: Dict[SegmentId, Set[str]] = {}

    def index_manifest(self, manifest: ManifestDescriptor) -> None:
        """Index a manifest and map its segment entries."""
        mid = manifest.manifest_id
        self._manifests[mid] = manifest
        for entry in manifest.segment_entries:
            seg_id = entry.metadata.segment_id
            if seg_id not in self._segment_to_manifests:
                self._segment_to_manifests[seg_id] = set()
            self._segment_to_manifests[seg_id].add(mid)

            sid = manifest.snapshot_id
            if seg_id not in self._segment_to_snapshots:
                self._segment_to_snapshots[seg_id] = set()
            self._segment_to_snapshots[seg_id].add(sid)

    def index_snapshot(self, snapshot: SnapshotDescriptor) -> None:
        """Index a snapshot descriptor."""
        self._snapshots[snapshot.snapshot_id] = snapshot

    def find_manifest(self, manifest_id: str) -> Optional[ManifestDescriptor]:
        """Look up manifest by ID."""
        return self._manifests.get(manifest_id)

    def find_snapshot(self, snapshot_id: SnapshotId) -> Optional[SnapshotDescriptor]:
        """Look up snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def find_segment(self, segment_id: SegmentId) -> List[SegmentDescriptor]:
        """Find segment descriptors for segment ID across indexed manifests."""
        results: List[SegmentDescriptor] = []
        for mid in self._segment_to_manifests.get(segment_id, set()):
            manifest = self._manifests.get(mid)
            if manifest:
                for entry in manifest.segment_entries:
                    if entry.metadata.segment_id == segment_id:
                        results.append(entry)
                        break
        return results

    def reverse_lookup(self, segment_id: SegmentId) -> Set[SnapshotId]:
        """Return set of snapshot IDs that reference a given segment ID."""
        return self._segment_to_snapshots.get(segment_id, set())

    def segment_usage(self, segment_id: SegmentId) -> int:
        """Return reference count (number of snapshots using this segment)."""
        return len(self.reverse_lookup(segment_id))

    def snapshot_lookup(self, repository_id: str) -> List[SnapshotDescriptor]:
        """Return all snapshots for a given repository ID."""
        return [s for s in self._snapshots.values() if s.repository_id == repository_id]
