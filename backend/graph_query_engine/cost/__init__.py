"""
DevBrain Graph Query Engine - Cost Model Subsystem Package.

Deterministic, explainable, execution-independent Cost Estimator and Statistics Pass (Step 4.4).
"""

from graph_query_engine.cost.aggregator import CostAggregator
from graph_query_engine.cost.cardinality import CardinalityEstimator
from graph_query_engine.cost.diagnostics import CostDiagnosticItem, CostDiagnostics
from graph_query_engine.cost.estimate import (
    CostEstimate,
    CostReport,
    OperatorCostBreakdown,
)
from graph_query_engine.cost.estimator import CostEstimator
from graph_query_engine.cost.estimators import (
    AggregateCostEstimator,
    BaseOperatorCostEstimator,
    DeduplicationCostEstimator,
    ExpandCostEstimator,
    FilterCostEstimator,
    GroupingCostEstimator,
    JoinCostEstimator,
    LimitCostEstimator,
    LookupCostEstimator,
    ProjectionCostEstimator,
    SortingCostEstimator,
)
from graph_query_engine.cost.resources import ResourceEstimator, ResourceRequirement
from graph_query_engine.cost.selectivity import SelectivityEstimator
from graph_query_engine.cost.serialization import (
    BinaryCostReportSerializer,
    CostReportSerializer,
    JSONCostReportSerializer,
    YAMLCostReportSerializer,
)
from graph_query_engine.cost.statistics import (
    EdgeStatistics,
    GraphStatisticsMetadata,
    IndexStatisticsMetadata,
    NodeStatistics,
    RepositoryStatisticsMetadata,
)
from graph_query_engine.cost.validation import (
    CostValidationReport,
    CostValidationViolation,
    CostValidator,
)
from graph_query_engine.cost.visitor import BaseCostVisitor, CostVisitor

__all__ = [
    # Cost Estimate Models
    "CostEstimate",
    "OperatorCostBreakdown",
    "CostReport",
    # Statistics Layer
    "NodeStatistics",
    "EdgeStatistics",
    "IndexStatisticsMetadata",
    "GraphStatisticsMetadata",
    "RepositoryStatisticsMetadata",
    # Estimation Engines
    "SelectivityEstimator",
    "CardinalityEstimator",
    "ResourceRequirement",
    "ResourceEstimator",
    "CostAggregator",
    # Operator Estimators
    "BaseOperatorCostEstimator",
    "LookupCostEstimator",
    "ExpandCostEstimator",
    "FilterCostEstimator",
    "ProjectionCostEstimator",
    "AggregateCostEstimator",
    "GroupingCostEstimator",
    "SortingCostEstimator",
    "DeduplicationCostEstimator",
    "JoinCostEstimator",
    "LimitCostEstimator",
    # Diagnostics & Validation
    "CostDiagnosticItem",
    "CostDiagnostics",
    "CostValidationViolation",
    "CostValidationReport",
    "CostValidator",
    # Visitor
    "CostVisitor",
    "BaseCostVisitor",
    # Serialization
    "CostReportSerializer",
    "JSONCostReportSerializer",
    "YAMLCostReportSerializer",
    "BinaryCostReportSerializer",
    # Cost Estimator Orchestrator
    "CostEstimator",
]
