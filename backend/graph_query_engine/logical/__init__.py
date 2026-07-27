"""
DevBrain Graph Query Engine - Logical Planner Package.

Execution-independent Logical Planner and Logical Plan intermediate representation (Step 4.3).
"""

from graph_query_engine.logical.builder import (
    LogicalOperatorBuilder,
    LogicalPlanBuilder,
    OperatorChainBuilder,
)
from graph_query_engine.logical.diagnostics import (
    LogicalPlannerDiagnosticItem,
    LogicalPlannerDiagnostics,
)
from graph_query_engine.logical.errors import (
    LogicalValidationError,
    LoweringError,
    PlannerInvariantError,
    UnknownOperatorError,
    UnsupportedQueryError,
)
from graph_query_engine.logical.lowering import (
    AggregateLoweringRule,
    ASTLoweringContext,
    ASTLoweringPipeline,
    ASTLoweringRule,
    BaseLoweringRule,
    DeduplicationLoweringRule,
    ExpandLoweringRule,
    FilterLoweringRule,
    GroupingLoweringRule,
    JoinLoweringRule,
    LimitLoweringRule,
    LookupLoweringRule,
    ProjectionLoweringRule,
    SortingLoweringRule,
)
from graph_query_engine.logical.operators import (
    LogicalAggregateOperator,
    LogicalDeduplicationOperator,
    LogicalExpandOperator,
    LogicalFilterOperator,
    LogicalGroupingOperator,
    LogicalJoinOperator,
    LogicalLimitOperator,
    LogicalLookupOperator,
    LogicalOperator,
    LogicalProjectionOperator,
    LogicalSortingOperator,
)
from graph_query_engine.logical.plan import (
    LogicalPlan,
    LogicalPlanMetadata,
    LogicalPlanNode,
    LogicalPlanStatistics,
)
from graph_query_engine.logical.planner import LogicalPlanner
from graph_query_engine.logical.serialization import (
    BinaryLogicalPlanSerializer,
    JSONLogicalPlanSerializer,
    LogicalPlanSerializer,
    YAMLLogicalPlanSerializer,
)
from graph_query_engine.logical.validation import (
    LogicalPlanValidator,
    LogicalValidationReport,
    LogicalValidationViolation,
)
from graph_query_engine.logical.version import LogicalPlanVersion
from graph_query_engine.logical.visitor import (
    BaseLogicalVisitor,
    LogicalVisitor,
    PrintLogicalVisitor,
    ValidationLogicalVisitor,
)

__all__ = [
    # Errors
    "UnknownOperatorError",
    "LoweringError",
    "LogicalValidationError",
    "UnsupportedQueryError",
    "PlannerInvariantError",
    # Versioning
    "LogicalPlanVersion",
    # Diagnostics
    "LogicalPlannerDiagnosticItem",
    "LogicalPlannerDiagnostics",
    # Operators
    "LogicalOperator",
    "LogicalLookupOperator",
    "LogicalExpandOperator",
    "LogicalFilterOperator",
    "LogicalProjectionOperator",
    "LogicalAggregateOperator",
    "LogicalGroupingOperator",
    "LogicalSortingOperator",
    "LogicalDeduplicationOperator",
    "LogicalJoinOperator",
    "LogicalLimitOperator",
    # Plan
    "LogicalPlanNode",
    "LogicalPlanMetadata",
    "LogicalPlanStatistics",
    "LogicalPlan",
    # Lowering
    "ASTLoweringContext",
    "ASTLoweringRule",
    "BaseLoweringRule",
    "LookupLoweringRule",
    "ExpandLoweringRule",
    "FilterLoweringRule",
    "ProjectionLoweringRule",
    "AggregateLoweringRule",
    "GroupingLoweringRule",
    "SortingLoweringRule",
    "DeduplicationLoweringRule",
    "LimitLoweringRule",
    "JoinLoweringRule",
    "ASTLoweringPipeline",
    # Validation
    "LogicalValidationViolation",
    "LogicalValidationReport",
    "LogicalPlanValidator",
    # Visitor
    "LogicalVisitor",
    "BaseLogicalVisitor",
    "PrintLogicalVisitor",
    "ValidationLogicalVisitor",
    # Builder
    "LogicalOperatorBuilder",
    "OperatorChainBuilder",
    "LogicalPlanBuilder",
    # Serialization
    "LogicalPlanSerializer",
    "JSONLogicalPlanSerializer",
    "YAMLLogicalPlanSerializer",
    "BinaryLogicalPlanSerializer",
    # Planner Orchestrator
    "LogicalPlanner",
]
