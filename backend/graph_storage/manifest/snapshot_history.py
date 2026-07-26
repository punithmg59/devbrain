"""
SnapshotHistory lineage and ancestry resolution tracking.
"""

from typing import List, Optional

from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.manifest.snapshot_repository import SnapshotRepository
from graph_storage.model import SnapshotId


class SnapshotHistory:
    """Version chain, parent tracking, and ancestry resolution for snapshots."""

    def __init__(self, snapshot_repository: SnapshotRepository):
        self.repository = snapshot_repository

    def get_parent(self, snapshot_id: SnapshotId) -> Optional[SnapshotDescriptor]:
        """Retrieve the direct parent snapshot descriptor."""
        snapshot = self.repository.load_snapshot(snapshot_id)
        if snapshot.parent_snapshot_id:
            return self.repository.load_snapshot(snapshot.parent_snapshot_id)
        return None

    def get_ancestors(self, snapshot_id: SnapshotId) -> List[SnapshotDescriptor]:
        """Retrieve all ancestor snapshots in order from root parent to snapshot."""
        ancestors: List[SnapshotDescriptor] = []
        curr_id: Optional[SnapshotId] = snapshot_id

        while curr_id is not None:
            curr_snapshot = self.repository.load_snapshot(curr_id)
            ancestors.append(curr_snapshot)
            curr_id = curr_snapshot.parent_snapshot_id

        return list(reversed(ancestors))

    def get_lineage(self, repository_id: str) -> List[SnapshotDescriptor]:
        """Retrieve all snapshots for a repository in chronological lineage order."""
        return self.repository.history(repository_id)
