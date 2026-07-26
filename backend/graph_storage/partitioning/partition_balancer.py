"""
PartitionBalancer planning component for evaluating partition utilization and generating rebalance plans.
"""

from dataclasses import dataclass
from typing import Dict, List
from graph_storage.partitioning.partition_descriptor import PartitionDescriptor
from graph_storage.partitioning.partition_policy import PartitionPolicy


@dataclass(frozen=True)
class CapacityReport:
    """Capacity report for partition utilization."""

    total_capacity_bytes: int
    total_used_bytes: int
    average_utilization_ratio: float
    overutilized_partitions: List[str]
    underutilized_partitions: List[str]


@dataclass(frozen=True)
class RebalanceRecommendation:
    """Recommendation for rebalancing segment allocation across partitions."""

    source_partition_id: str
    target_partition_id: str
    estimated_transfer_bytes: int
    reason: str


class PartitionBalancer:
    """Balancer planning component analyzing partition utilization and capacity."""

    def __init__(self, policy: PartitionPolicy = PartitionPolicy()):
        self.policy = policy

    def analyze(self, partitions: List[PartitionDescriptor]) -> CapacityReport:
        """Analyze partition capacity and utilization."""
        if not partitions:
            return CapacityReport(0, 0, 0.0, [], [])

        total_cap = sum(p.capacity_bytes for p in partitions)
        total_used = sum(p.current_size_bytes for p in partitions)
        avg_util = (total_used / total_cap) if total_cap > 0 else 0.0

        overutilized = []
        underutilized = []

        for p in partitions:
            util = (p.current_size_bytes / p.capacity_bytes) if p.capacity_bytes > 0 else 0.0
            if util > self.policy.rebalance_threshold_ratio:
                overutilized.append(p.partition_id.value)
            elif util < (self.policy.target_utilization_ratio * 0.5):
                underutilized.append(p.partition_id.value)

        return CapacityReport(
            total_capacity_bytes=total_cap,
            total_used_bytes=total_used,
            average_utilization_ratio=avg_util,
            overutilized_partitions=overutilized,
            underutilized_partitions=underutilized,
        )

    def recommend(self, partitions: List[PartitionDescriptor]) -> List[RebalanceRecommendation]:
        """Generate rebalance recommendations (planning only, no automatic movement)."""
        report = self.analyze(partitions)
        recommendations: List[RebalanceRecommendation] = []

        if not report.overutilized_partitions or not report.underutilized_partitions:
            return recommendations

        for over_id in report.overutilized_partitions:
            for under_id in report.underutilized_partitions:
                recommendations.append(
                    RebalanceRecommendation(
                        source_partition_id=over_id,
                        target_partition_id=under_id,
                        estimated_transfer_bytes=10485760,  # Nominal 10MB chunk suggestion
                        reason=f"Partition {over_id} exceeds rebalance threshold ratio ({self.policy.rebalance_threshold_ratio})",
                    )
                )

        return recommendations

    def rebalance_plan(self, partitions: List[PartitionDescriptor]) -> Dict[str, List[RebalanceRecommendation]]:
        """Return structured rebalance plan."""
        recs = self.recommend(partitions)
        return {"recommendations": recs}
