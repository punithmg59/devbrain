# Export core symbols for the optimizer package

from .version import OptimizerVersion, OptimizationRuleVersion, CompatibilityVersion
from .contracts import PhysicalPlan, OptimizedPhysicalPlan
from .planner import PlannerOptimizer
from .pipeline import OptimizationPipeline, OptimizationPipelineBuilder
from .scheduler import OptimizationScheduler
from .registry import OptimizationRuleRegistry
from .phase import OptimizationPhase
from .context import OptimizationRuleContext
from .result import OptimizationRuleResult
from .metrics import OptimizationMetrics
from .report import OptimizationReport
from .diagnostics import OptimizationDiagnostics
from .validation import OptimizerValidator
from .builder import OptimizedPlanBuilder, OptimizationReportBuilder, RuleBuilder
from .rules import OptimizationRule
from .rules_impl import (
    FilterPushdownRule,
    ProjectionPushdownRule,
    OperatorFusionRule,
    RedundantFilterEliminationRule,
    RedundantProjectionEliminationRule,
    ConstantFoldingRule,
    DeadCodeEliminationRule,
    JoinReorderingRule,
    ExpandOptimizationRule,
    SubqueryUnrollingRule,
    LimitPushdownRule,
    ScanOptimizationRule,
    IndexScanSelectionRule,
)
from .visitor import (
    OptimizationVisitor,
    RuleInspectionVisitor,
    PlanComparisonVisitor,
    ValidationVisitor,
    MermaidDiagramVisitor,
)
from .serialization import (
    JSONOptimizerSerializer,
    YAMLOptimizerSerializer,
    BinaryOptimizerSerializer,
)

__all__ = [
    "OptimizerVersion",
    "OptimizationRuleVersion",
    "CompatibilityVersion",
    "PhysicalPlan",
    "OptimizedPhysicalPlan",
    "PlannerOptimizer",
    "OptimizationPipeline",
    "OptimizationPipelineBuilder",
    "OptimizationScheduler",
    "OptimizationRuleRegistry",
    "OptimizationPhase",
    "OptimizationRuleContext",
    "OptimizationRuleResult",
    "OptimizationMetrics",
    "OptimizationReport",
    "OptimizationDiagnostics",
    "OptimizerValidator",
    "OptimizedPlanBuilder",
    "OptimizationReportBuilder",
    "RuleBuilder",
    "OptimizationRule",
    "FilterPushdownRule",
    "ProjectionPushdownRule",
    "OperatorFusionRule",
    "RedundantFilterEliminationRule",
    "RedundantProjectionEliminationRule",
    "ConstantFoldingRule",
    "DeadCodeEliminationRule",
    "JoinReorderingRule",
    "ExpandOptimizationRule",
    "SubqueryUnrollingRule",
    "LimitPushdownRule",
    "ScanOptimizationRule",
    "IndexScanSelectionRule",
    "OptimizationVisitor",
    "RuleInspectionVisitor",
    "PlanComparisonVisitor",
    "ValidationVisitor",
    "MermaidDiagramVisitor",
    "JSONOptimizerSerializer",
    "YAMLOptimizerSerializer",
    "BinaryOptimizerSerializer",
]
