"""
Selectivity Estimator Engine.

Calculates estimated predicate filter selectivity values (0.0 to 1.0)
using statistical hints and predicate AST node types.
"""

from typing import Optional
from graph_query_engine.cost.statistics import GraphStatisticsMetadata
from graph_query_engine.query.predicates import (
    AndPredicate,
    AttributePredicate,
    ContainsPredicate,
    EndsWithPredicate,
    EqualityPredicate,
    ExistsPredicate,
    NodePredicate,
    NotPredicate,
    OrPredicate,
    QueryPredicate,
    RangePredicate,
    RelationshipPredicate,
    StartsWithPredicate,
)


class SelectivityEstimator:
    """
    Pure functional estimator computing predicate filter selectivity (0.0 to 1.0).
    """

    @classmethod
    def estimate_predicate_selectivity(
        cls,
        predicate: Optional[QueryPredicate],
        stats: Optional[GraphStatisticsMetadata] = None,
    ) -> float:
        """
        Estimates expected selectivity factor for a QueryPredicate node.
        """
        if predicate is None:
            return 1.0

        if isinstance(predicate, EqualityPredicate):
            # Equality on primary/unique attributes has high selectivity (e.g. 0.01 - 0.05)
            if predicate.property_name in ("id", "node_id", "symbol_id", "qualified_name"):
                return 0.001
            return 0.05

        elif isinstance(predicate, RangePredicate):
            # Range predicates typically filter 20% to 30% of rows
            return 0.25

        elif isinstance(predicate, ContainsPredicate):
            return 0.15

        elif isinstance(predicate, StartsWithPredicate):
            return 0.10

        elif isinstance(predicate, EndsWithPredicate):
            return 0.10

        elif isinstance(predicate, ExistsPredicate):
            return 0.80

        elif isinstance(predicate, NodePredicate):
            # Node type matching based on node_type_counts
            if predicate.node_type and stats:
                cnt = stats.nodes.node_type_counts.get(predicate.node_type.upper(), 1000)
                tot = max(stats.nodes.total_node_count, 1)
                return min(max(cnt / tot, 0.001), 1.0)
            return 0.20

        elif isinstance(predicate, RelationshipPredicate):
            if predicate.relationship_type and stats:
                rel_str = str(predicate.relationship_type.value).upper()
                cnt = stats.edges.relationship_type_counts.get(rel_str, 5000)
                tot = max(stats.edges.total_edge_count, 1)
                return min(max(cnt / tot, 0.001), 1.0)
            return 0.30

        elif isinstance(predicate, AttributePredicate):
            return cls.estimate_predicate_selectivity(None, stats)

        elif isinstance(predicate, AndPredicate):
            # AND: s = s1 * s2 * ...
            sel = 1.0
            for sub in predicate.predicates:
                sel *= cls.estimate_predicate_selectivity(sub, stats)
            return max(sel, 0.0001)

        elif isinstance(predicate, OrPredicate):
            # OR: s = 1 - (1 - s1) * (1 - s2) ...
            neg = 1.0
            for sub in predicate.predicates:
                sub_s = cls.estimate_predicate_selectivity(sub, stats)
                neg *= (1.0 - sub_s)
            return min(max(1.0 - neg, 0.0001), 1.0)

        elif isinstance(predicate, NotPredicate):
            sub_s = cls.estimate_predicate_selectivity(predicate.predicate, stats)
            return max(1.0 - sub_s, 0.0001)

        return 0.50


__all__ = ["SelectivityEstimator"]
