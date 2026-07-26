"""
PartitionTopology hierarchy abstraction modeling partition zones, racks, and placement neighbors.
"""

from typing import Dict, List, Optional, Set

from graph_storage.model import PartitionId
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor


class PartitionTopology:
    """Topology hierarchy abstraction modeling partition zones, racks, and placement neighbors."""

    def __init__(self):
        self._partitions: Dict[PartitionId, PartitionDescriptor] = {}
        self._zones: Dict[PartitionId, str] = {}
        self._parents: Dict[PartitionId, Optional[PartitionId]] = {}
        self._children: Dict[PartitionId, Set[PartitionId]] = {}

    def register_partition(
        self,
        descriptor: PartitionDescriptor,
        zone: str = "default_zone",
        parent_id: Optional[PartitionId] = None,
    ) -> None:
        """Register a partition descriptor into the topology hierarchy."""
        pid = descriptor.partition_id
        self._partitions[pid] = descriptor
        self._zones[pid] = zone
        self._parents[pid] = parent_id
        if pid not in self._children:
            self._children[pid] = set()
        if parent_id:
            if parent_id not in self._children:
                self._children[parent_id] = set()
            self._children[parent_id].add(pid)

    def lookup(self, partition_id: PartitionId) -> Optional[PartitionDescriptor]:
        """Look up partition descriptor by ID."""
        return self._partitions.get(partition_id)

    def zone(self, partition_id: PartitionId) -> str:
        """Get zone name for partition."""
        return self._zones.get(partition_id, "default_zone")

    def parent(self, partition_id: PartitionId) -> Optional[PartitionDescriptor]:
        """Retrieve parent partition descriptor."""
        parent_id = self._parents.get(partition_id)
        return self.lookup(parent_id) if parent_id else None

    def children(self, partition_id: PartitionId) -> List[PartitionDescriptor]:
        """Retrieve child partition descriptors."""
        child_ids = self._children.get(partition_id, set())
        return [self._partitions[cid] for cid in child_ids if cid in self._partitions]

    def neighbors(self, partition_id: PartitionId) -> List[PartitionDescriptor]:
        """Retrieve neighbor partitions residing in the same zone."""
        target_zone = self.zone(partition_id)
        return [p for pid, p in self._partitions.items() if pid != partition_id and self.zone(pid) == target_zone]

    def hierarchy(self) -> Dict[str, List[str]]:
        """Return map of zones to partition IDs."""
        result: Dict[str, List[str]] = {}
        for pid, zone_name in self._zones.items():
            if zone_name not in result:
                result[zone_name] = []
            result[zone_name].append(pid.value)
        return result
