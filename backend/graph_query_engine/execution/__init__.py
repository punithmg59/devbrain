"""
DevBrain Graph Query Engine - Execution Plan Subsystem Package.

Execution-independent Execution Planner and Stage Dependency Graph (Step 4.6).
"""

from graph_query_engine.execution.builder import (
    ExecutionPlanBuilder,
    ExecutionStageBuilder,
    PipelineGraphBuilder,
)
from graph_query_engine.execution.diagnostics import (
    ExecutionPlannerDiagnosticItem,
    ExecutionPlannerDiagnostics,
)
from graph_query_engine.execution.operators import (
    AggregationExecutionOperator,
    DeduplicationExecutionOperator,
    ExecutionOperator,
    ExpandExecutionOperator,
    FilterExecutionOperator,
    HashJoinExecutionOperator,
    IndexLookupExecutionOperator,
    LimitExecutionOperator,
    MergeJoinExecutionOperator,
    NestedLoopExecutionOperator,
    ProjectionExecutionOperator,
    SequentialLookupExecutionOperator,
    SortingExecutionOperator,
)
from graph_query_engine.execution.pipeline import (
    ExecutionPipeline,
    StageDependencyGraph,
)
from graph_query_engine.execution.plan import (
    ExecutionMetadata,
    ExecutionPlan,
)
from graph_query_engine.execution.planner import ExecutionPlanner
from graph_query_engine.execution.serialization import (
    BinaryExecutionPlanSerializer,
    ExecutionPlanSerializer,
    JSONExecutionPlanSerializer,
    YAMLExecutionPlanSerializer,
)
from graph_query_engine.execution.stage import ExecutionStage
from graph_query_engine.execution.validation import (
    ExecutionPlanValidator,
    ExecutionValidationReport,
    ExecutionValidationViolation,
)
from graph_query_engine.execution.version import ExecutionPlanVersion
from graph_query_engine.execution.visitor import (
    BaseExecutionVisitor,
    ExecutionVisitor,
    PrintExecutionVisitor,
    ValidationExecutionVisitor,
)

__all__ = [
    # Versioning
    "ExecutionPlanVersion",
    # Diagnostics
    "ExecutionPlannerDiagnosticItem",
    "ExecutionPlannerDiagnostics",
    # Operators
    "ExecutionOperator",
    "IndexLookupExecutionOperator",
    "SequentialLookupExecutionOperator",
    "ExpandExecutionOperator",
    "FilterExecutionOperator",
    "ProjectionExecutionOperator",
    "AggregationExecutionOperator",
    "SortingExecutionOperator",
    "DeduplicationExecutionOperator",
    "HashJoinExecutionOperator",
    "MergeJoinExecutionOperator",
    "NestedLoopExecutionOperator",
    "LimitExecutionOperator",
    # Stages & Pipeline
    "ExecutionStage",
    "StageDependencyGraph",
    "ExecutionPipeline",
    # Plan
    "ExecutionMetadata",
    "ExecutionPlan",
    # Validation
    "ExecutionValidationViolation",
    "ExecutionValidationReport",
    "ExecutionPlanValidator",
    # Visitor
    "ExecutionVisitor",
    "BaseExecutionVisitor",
    "PrintExecutionVisitor",
    "ValidationExecutionVisitor",
    # Builders
    "ExecutionStageBuilder",
    "PipelineGraphBuilder",
    "ExecutionPlanBuilder",
    # Serialization
    "ExecutionPlanSerializer",
    "JSONExecutionPlanSerializer",
    "YAMLExecutionPlanSerializer",
    "BinaryExecutionPlanSerializer",
    # Planner Orchestrator
    "ExecutionPlanner",
]
