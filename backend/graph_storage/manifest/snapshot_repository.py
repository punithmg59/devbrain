"""
SnapshotRepository implementation for persisting and querying snapshot descriptors.
"""

import json
from typing import Dict, List, Optional

from graph_storage.exceptions import GraphStorageError, SegmentNotFoundError
from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.model import SegmentId, SnapshotId, StorageKey, VersionRef
from graph_storage.segment.segment_repository import SegmentRepository


class SnapshotRepository:
    """Repository for snapshot descriptors and repository lineage queries."""

    def __init__(self, segment_repository: SegmentRepository):
        self.segment_repository = segment_repository
        self._snapshot_store: Dict[SnapshotId, SnapshotDescriptor] = {}
        self._repo_snapshots: Dict[str, List[SnapshotId]] = {}

    def _snapshot_segment_id(self, snapshot_id: SnapshotId) -> SegmentId:
        return SegmentId(f"snapshot_{snapshot_id.value}")

    def save_snapshot(self, snapshot: SnapshotDescriptor) -> None:
        """Save a snapshot descriptor."""
        self._snapshot_store[snapshot.snapshot_id] = snapshot
        repo_id = snapshot.repository_id
        if repo_id not in self._repo_snapshots:
            self._repo_snapshots[repo_id] = []
        if snapshot.snapshot_id not in self._repo_snapshots[repo_id]:
            self._repo_snapshots[repo_id].append(snapshot.snapshot_id)

        snapshot_dict = {
            "snapshot_id": snapshot.snapshot_id.value,
            "repository_id": snapshot.repository_id,
            "version": f"{snapshot.version.major}.{snapshot.version.minor}.{snapshot.version.patch}",
            "created_time": snapshot.created_time,
            "segment_count": snapshot.segment_count,
            "total_size": snapshot.total_size,
            "checksum": snapshot.checksum,
            "manifest_location": snapshot.manifest_location.value,
            "parent_snapshot_id": snapshot.parent_snapshot_id.value if snapshot.parent_snapshot_id else None,
        }
        payload = json.dumps(snapshot_dict).encode("utf-8")
        self.segment_repository.save(self._snapshot_segment_id(snapshot.snapshot_id), payload)

    def load_snapshot(self, snapshot_id: SnapshotId) -> SnapshotDescriptor:
        """Load a snapshot descriptor."""
        if snapshot_id in self._snapshot_store:
            return self._snapshot_store[snapshot_id]

        seg_id = self._snapshot_segment_id(snapshot_id)
        if not self.segment_repository.exists(seg_id):
            raise SegmentNotFoundError(f"Snapshot not found: {snapshot_id.value}")

        payload = self.segment_repository.load(seg_id)
        d = json.loads(payload.decode("utf-8"))

        v_parts = [int(p) for p in d["version"].split(".")]
        parent_id = SnapshotId(d["parent_snapshot_id"]) if d["parent_snapshot_id"] else None

        snapshot = SnapshotDescriptor(
            snapshot_id=SnapshotId(d["snapshot_id"]),
            repository_id=d["repository_id"],
            version=VersionRef(v_parts[0], v_parts[1], v_parts[2]),
            created_time=d["created_time"],
            segment_count=d["segment_count"],
            total_size=d["total_size"],
            checksum=d["checksum"],
            manifest_location=StorageKey(d["manifest_location"]),
            parent_snapshot_id=parent_id,
        )
        self._snapshot_store[snapshot_id] = snapshot
        return snapshot

    def delete_snapshot(self, snapshot_id: SnapshotId) -> bool:
        """Delete a snapshot descriptor."""
        snapshot = self._snapshot_store.pop(snapshot_id, None)
        if snapshot and snapshot.repository_id in self._repo_snapshots:
            if snapshot_id in self._repo_snapshots[snapshot.repository_id]:
                self._repo_snapshots[snapshot.repository_id].remove(snapshot_id)
        return self.segment_repository.delete(self._snapshot_segment_id(snapshot_id))

    def exists(self, snapshot_id: SnapshotId) -> bool:
        """Check if snapshot exists."""
        if snapshot_id in self._snapshot_store:
            return True
        return self.segment_repository.exists(self._snapshot_segment_id(snapshot_id))

    def history(self, repository_id: str) -> List[SnapshotDescriptor]:
        """Retrieve full snapshot history for a repository in creation order."""
        snapshot_ids = self._repo_snapshots.get(repository_id, [])
        descriptors = [self.load_snapshot(sid) for sid in snapshot_ids]
        return sorted(descriptors, key=lambda s: s.created_time)

    def latest(self, repository_id: str) -> Optional[SnapshotDescriptor]:
        """Retrieve the latest snapshot for a repository."""
        hist = self.history(repository_id)
        return hist[-1] if hist else None
