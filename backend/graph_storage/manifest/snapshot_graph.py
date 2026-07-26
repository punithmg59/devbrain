"""
SnapshotGraph implementation modeling snapshot DAG relationships, ancestry, and branching.
"""

from typing import Dict, List, Optional, Set

from graph_storage.manifest.snapshot_descriptor import SnapshotDescriptor
from graph_storage.model import SnapshotId


class SnapshotGraph:
    """DAG abstraction modeling snapshot relationships, branches, and lineage."""

    def __init__(self):
        self._nodes: Dict[SnapshotId, SnapshotDescriptor] = {}
        self._children: Dict[SnapshotId, Set[SnapshotId]] = {}
        self._parents: Dict[SnapshotId, Optional[SnapshotId]] = {}

    def register_snapshot(self, snapshot: SnapshotDescriptor) -> None:
        """Register a snapshot descriptor in the graph DAG."""
        sid = snapshot.snapshot_id
        self._nodes[sid] = snapshot
        if sid not in self._children:
            self._children[sid] = set()

        parent_id = snapshot.parent_snapshot_id
        self._parents[sid] = parent_id

        if parent_id:
            if parent_id not in self._children:
                self._children[parent_id] = set()
            self._children[parent_id].add(sid)

    def lookup(self, snapshot_id: SnapshotId) -> Optional[SnapshotDescriptor]:
        """Look up a snapshot descriptor by ID."""
        return self._nodes.get(snapshot_id)

    def parent(self, snapshot_id: SnapshotId) -> Optional[SnapshotDescriptor]:
        """Retrieve direct parent snapshot descriptor."""
        parent_id = self._parents.get(snapshot_id)
        return self.lookup(parent_id) if parent_id else None

    def children(self, snapshot_id: SnapshotId) -> List[SnapshotDescriptor]:
        """Retrieve direct child snapshot descriptors."""
        child_ids = self._children.get(snapshot_id, set())
        return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    def ancestors(self, snapshot_id: SnapshotId) -> List[SnapshotDescriptor]:
        """Retrieve all ancestor snapshots in order from root parent down to target."""
        result: List[SnapshotDescriptor] = []
        curr = self.parent(snapshot_id)
        while curr is not None:
            result.append(curr)
            curr = self.parent(curr.snapshot_id)
        return list(reversed(result))

    def descendants(self, snapshot_id: SnapshotId) -> List[SnapshotDescriptor]:
        """Retrieve all descendant snapshots in BFS order."""
        result: List[SnapshotDescriptor] = []
        queue = list(self.children(snapshot_id))
        visited: Set[SnapshotId] = set()

        while queue:
            node = queue.pop(0)
            if node.snapshot_id not in visited:
                visited.add(node.snapshot_id)
                result.append(node)
                queue.extend(self.children(node.snapshot_id))

        return result

    def is_ancestor(self, possible_ancestor_id: SnapshotId, snapshot_id: SnapshotId) -> bool:
        """Check if possible_ancestor_id is an ancestor of snapshot_id."""
        ancestor_ids = {a.snapshot_id for a in self.ancestors(snapshot_id)}
        return possible_ancestor_id in ancestor_ids

    def is_descendant(self, possible_descendant_id: SnapshotId, snapshot_id: SnapshotId) -> bool:
        """Check if possible_descendant_id is a descendant of snapshot_id."""
        descendant_ids = {d.snapshot_id for d in self.descendants(snapshot_id)}
        return possible_descendant_id in descendant_ids
