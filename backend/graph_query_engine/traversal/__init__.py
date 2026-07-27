# backend/graph_query_engine/traversal/__init__.py
"""DevBrain Graph Query Engine - Traversal Engine Subsystem.
Public exports for graph traversal execution, algorithms, operators, results, and visitors.
"""

from .version import TraversalEngineVersion
from .context import TraversalLimits, TraversalExecutionContext
from .metrics import TraversalMetrics
from .diagnostics import TraversalDiagnosticRecord, TraversalDiagnostics
from .result import TraversalPath, TraversalResult
from .validation import TraversalValidationViolation, TraversalValidationReport, TraversalValidator
from .engine import TraversalEngine
from .pipeline import TraversalPipeline
from .contracts import ITraversalRegistry, ITraversalStrategy

from .algorithms import (
    BaseGraphAlgorithm,
    BreadthFirstSearch,
    DepthFirstSearch,
    BidirectionalSearch,
    ReachabilityAnalysis,
    ShortestPath,
    ConnectedComponents,
    TopologicalTraversal,
    CycleDetection,
    AncestorDiscovery,
    DescendantDiscovery,
    NeighborhoodExpansion,
)

from .operators import (
    TraversalOperator,
    NodeScanOperator,
    IndexLookupOperator,
    NeighborExpandOperator,
    EdgeFilterOperator,
    PathExpandOperator,
    TraversalMergeOperator,
    TraversalUnionOperator,
    TraversalIntersectionOperator,
    TraversalLimitOperator,
    TraversalSortOperator,
    TraversalDeduplicateOperator,
    TraversalAggregateOperator,
    TraversalProjectOperator,
    TraversalCollectOperator,
    TraversalResultBuilderOperator,
)

from .builder import (
    TraversalResultBuilder,
    ExecutionContextBuilder,
    TraversalReportBuilder,
    TraversalMetricsBuilder,
)

from .visitor import (
    TraversalVisitor,
    TraversalInspectionVisitor,
    TraversalValidationVisitor,
    TraversalPrintingVisitor,
    TraversalStatisticsVisitor,
    MermaidGraphVisitor,
)

from .serialization import (
    JSONTraversalSerializer,
    YAMLTraversalSerializer,
    BinaryTraversalSerializer,
)

__all__ = [
    "ITraversalRegistry",
    "ITraversalStrategy",
    "TraversalEngineVersion",
    "TraversalLimits",
    "TraversalExecutionContext",
    "TraversalMetrics",
    "TraversalDiagnosticRecord",
    "TraversalDiagnostics",
    "TraversalPath",
    "TraversalResult",
    "TraversalValidationViolation",
    "TraversalValidationReport",
    "TraversalValidator",
    "TraversalEngine",
    "TraversalPipeline",
    "BaseGraphAlgorithm",
    "BreadthFirstSearch",
    "DepthFirstSearch",
    "BidirectionalSearch",
    "ReachabilityAnalysis",
    "ShortestPath",
    "ConnectedComponents",
    "TopologicalTraversal",
    "CycleDetection",
    "AncestorDiscovery",
    "DescendantDiscovery",
    "NeighborhoodExpansion",
    "TraversalOperator",
    "NodeScanOperator",
    "IndexLookupOperator",
    "NeighborExpandOperator",
    "EdgeFilterOperator",
    "PathExpandOperator",
    "TraversalMergeOperator",
    "TraversalUnionOperator",
    "TraversalIntersectionOperator",
    "TraversalLimitOperator",
    "TraversalSortOperator",
    "TraversalDeduplicateOperator",
    "TraversalAggregateOperator",
    "TraversalProjectOperator",
    "TraversalCollectOperator",
    "TraversalResultBuilderOperator",
    "TraversalResultBuilder",
    "ExecutionContextBuilder",
    "TraversalReportBuilder",
    "TraversalMetricsBuilder",
    "TraversalVisitor",
    "TraversalInspectionVisitor",
    "TraversalValidationVisitor",
    "TraversalPrintingVisitor",
    "TraversalStatisticsVisitor",
    "MermaidGraphVisitor",
    "JSONTraversalSerializer",
    "YAMLTraversalSerializer",
    "BinaryTraversalSerializer",
]
