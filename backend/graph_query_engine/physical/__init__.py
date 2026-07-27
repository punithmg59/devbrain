"""
DevBrain Graph Query Engine - Physical Planner Subsystem Package.

Execution-independent Physical Planner and Strategy Selector (Step 4.5).
"""

from graph_query_engine.physical.builder import (
    ExecutionPipelineBuilder,
    PhysicalOperatorBuilder,
    PhysicalPlanBuilder,
)
from graph_query_engine.physical.diagnostics import (
    PhysicalPlannerDiagnosticItem,
    PhysicalPlannerDiagnostics,
)
from graph_query_engine.physical.operators import (
    AggregationExecutionPhysicalOperator,
    BidirectionalExpandPhysicalOperator,
    BreadthExpandPhysicalOperator,
    DeduplicationExecutionPhysicalOperator,
    DepthExpandPhysicalOperator,
    FilterPushdownPhysicalOperator,
    HashJoinPhysicalOperator,
    HierarchyExpandPhysicalOperator,
    IndexLookupPhysicalOperator,
    LimitExecutionPhysicalOperator,
    MergeJoinPhysicalOperator,
    NestedLoopJoinPhysicalOperator,
    PathExpandPhysicalOperator,
    PhysicalOperator,
    ProjectionPushdownPhysicalOperator,
    SequentialLookupPhysicalOperator,
    SortingExecutionPhysicalOperator,
)
from graph_query_engine.physical.plan import (
    PhysicalPlan,
    PhysicalPlanMetadata,
    PhysicalPlanNode,
)
from graph_query_engine.physical.planner import PhysicalPlanner
from graph_query_engine.physical.serialization import (
    BinaryPhysicalPlanSerializer,
    JSONPhysicalPlanSerializer,
    PhysicalPlanSerializer,
    YAMLPhysicalPlanSerializer,
)
from graph_query_engine.physical.strategy import (
    ExpandStrategySelector,
    JoinStrategySelector,
    LookupStrategySelector,
    PushdownStrategySelector,
)
from graph_query_engine.physical.validation import (
    PhysicalPlanValidator,
    PhysicalValidationReport,
    PhysicalValidationViolation,
)
from graph_query_engine.physical.version import PhysicalPlanVersion
from graph_query_engine.physical.visitor import (
    BasePhysicalVisitor,
    PhysicalVisitor,
    PrintPhysicalVisitor,
    ValidationPhysicalVisitor,
)

__all__ = [
    # Versioning
    "PhysicalPlanVersion",
    # Diagnostics
    "PhysicalPlannerDiagnosticItem",
    "PhysicalPlannerDiagnostics",
    # Operators
    "PhysicalOperator",
    "IndexLookupPhysicalOperator",
    "SequentialLookupPhysicalOperator",
    "BreadthExpandPhysicalOperator",
    "DepthExpandPhysicalOperator",
    "BidirectionalExpandPhysicalOperator",
    "PathExpandPhysicalOperator",
    "HierarchyExpandPhysicalOperator",
    "FilterPushdownPhysicalOperator",
    "ProjectionPushdownPhysicalOperator",
    "HashJoinPhysicalOperator",
    "NestedLoopJoinPhysicalOperator",
    "MergeJoinPhysicalOperator",
    "AggregationExecutionPhysicalOperator",
    "SortingExecutionPhysicalOperator",
    "DeduplicationExecutionPhysicalOperator",
    "LimitExecutionPhysicalOperator",
    # Strategies
    "LookupStrategySelector",
    "ExpandStrategySelector",
    "JoinStrategySelector",
    "PushdownStrategySelector",
    # Plan
    "PhysicalPlanNode",
    "PhysicalPlanMetadata",
    "PhysicalPlan",
    # Validation
    "PhysicalValidationViolation",
    "PhysicalValidationReport",
    "PhysicalPlanValidator",
    # Visitor
    "PhysicalVisitor",
    "BasePhysicalVisitor",
    "PrintPhysicalVisitor",
    "ValidationPhysicalVisitor",
    # Builders
    "PhysicalOperatorBuilder",
    "ExecutionPipelineBuilder",
    "PhysicalPlanBuilder",
    # Serialization
    "PhysicalPlanSerializer",
    "JSONPhysicalPlanSerializer",
    "YAMLPhysicalPlanSerializer",
    "BinaryPhysicalPlanSerializer",
    # Planner Orchestrator
    "PhysicalPlanner",
]
